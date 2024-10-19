import uproot
import os
import shutil
import pandas as pd
import re
import matplotlib.pyplot as plt
from pathlib import Path

import torch
import torch.nn as nn

from opengate.base import GateObject
from opengate.exception import fatal
from opengate.utility import delete_folder_contents


# This extracts the number from the filename.
# Helpful for sorting the csv files when fetched.
def extract_number(filename):
    match = re.search(r"\d+", filename)
    if match:
        return int(match.group())
    return 0


# Generator class architecture for 3x3x3 crystal
class WGANGenerator(nn.Module):

    def __init__(self, input_dim, output_dim, hidden_dim, labels_len):
        super(WGANGenerator, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim + labels_len, hidden_dim),
            nn.ReLU(True),
            nn.Linear(hidden_dim, 2 * hidden_dim),
            nn.ReLU(True),
            nn.Linear(2 * hidden_dim, 4 * hidden_dim),
            nn.ReLU(True),
            nn.Linear(4 * hidden_dim, output_dim),
        )

    def forward(self, x):
        return self.model(x)


def _setter_hook_input_phsp_actor(self, input_phsp_actor):
    if input_phsp_actor is not None:
        if self.simulation is not None and self.simulation != input_phsp_actor.simulation:
            fatal("The input_phsp_actor refers to a different simulation than this oOtiGAN. ")
        self.simulation = input_phsp_actor.simulation
        self.root_file_path = input_phsp_actor.get_output_path()
    return input_phsp_actor


def process_root_output_into_events(df_combined):

    position_x = df_combined["Position_X"].to_numpy()
    position_y = df_combined["Position_Y"].to_numpy()
    position_z = df_combined["Position_Z"].to_numpy()
    particle_types = df_combined["ParticleType"].to_numpy()

    # variables
    events = {}  # will store all the events
    current_event = []
    event_id = 0

    # flag to check if gamma is followed by electrons or photons
    gamma_has_electrons_or_photons = False

    # counts the occurence of optical photons in current event
    optical_photon_count = 0

    # process each particle and segregate into events
    for index, (ptype, x, y, z) in enumerate(
            zip(particle_types, position_x, position_y, position_z)
    ):
        if ptype == "gamma":
            # store the previous event if it started with a gamma
            # and is followed by electrons or photons
            if current_event and gamma_has_electrons_or_photons:
                current_event.append(
                    {
                        "type": "opticalphoton",
                        "optical_photon_count": optical_photon_count,
                    }
                )
                events[event_id] = current_event
                event_id += 1
                optical_photon_count = 0
            # if it is a new event, add the gamma particle to it
            current_event = [
                {"index": index, "type": ptype, "x": x, "y": y, "z": z}
            ]
            gamma_has_electrons_or_photons = False
        elif ptype == "opticalphoton":
            # if the particle is optical photon, just increment the count
            optical_photon_count += 1
            gamma_has_electrons_or_photons = True
        elif ptype == "e-":
            # Only add e- if there is an ongoing event (started by gamma)
            if current_event:
                current_event.append(
                    {"index": index, "type": ptype, "x": x, "y": y, "z": z}
                )
                gamma_has_electrons_or_photons = True

    # Store the last event if it is not empty
    if len(current_event) > 1:
        current_event.append(
            {"type": "opticalphoton", "optical_photon_count": optical_photon_count}
        )
        events[event_id] = current_event

    return events


class OptiGAN(GateObject):
    """
    Class Responsibilities:
    - Retrieve the necessary data from the root file.
    - Separate and organize data based on gamma events.
    - Load and initialize the OptiGAN model.
    - Extract and process inputs for use with OptiGAN.
    """

    user_info_defaults = {
        "output_folder":
            ("optigan", {"doc": "Folder where the OptiGAN saves output (some of it in subdirectories)."
                         "It is relative to the simulation.output_dir if a simulation is known to OptiGAN, "
                         "which is the case if the option 'input_phsp_actor' is set "
                         "or if 'my_optigan.simulation=...' is set. "
                         "Otherwise, output_folder is understood to be relative to the current working directory. "
                         "output_folder can also be an absolute path."
                         }),
        "input_phsp_actor":
            (None, {"doc": "The phase space actor that generates the training data input for this OptiGAN. "
                           "Its output path and the reference to the simulation are automatically picked up. ",
                    "setter_hook": _setter_hook_input_phsp_actor}
             ),
        "root_file_path":
            (None, {"doc": "Path to the root file containing training phase space data. "
                           "This input is alternative to input_phsp_actor in case the OptiGAN is run stand-alone, "
                           "i.e. without a GATE simulation.",
                    }
             ),
        "path_to_optigan_model":
            (Path(os.path.dirname(__file__)) / "optigan_models" / "model_3341.pt",
             {"doc": "Path to the .pt model file used to create the GAN. "
                     "The default model that currently ships with GATE 10 (model_3341.pt) "
                     "is for 3*3*3 crystal dimension "
                     "and has been trained by the team at UC Davis. ",
              }
             ),
    }

    def __init__(self, *args, **kwargs):
        # pick up the input_phsp_actor
        input_phsp_actor = kwargs.pop('input_phsp_actor', None)
        root_file_path = kwargs.pop('root_file_path', None)
        kwargs['name'] = 'optigan'
        super().__init__(*args, **kwargs)
        # and set it once the base class has processed all user inout parameters
        if root_file_path is None and input_phsp_actor is None:
            fatal("An OptiGAN requires either a root_file_path or an input_phsp_actor.")

        # the output path from input_phsp_actor overrides the root_file_path
        self.root_file_path = root_file_path
        self.input_phsp_actor = input_phsp_actor

        # paths: they are set in initialize()
        self.optigan_input_folder = None
        self.optigan_output_folder = None
        self.optigan_csv_output_folder = None
        self.optigan_plots_folder = None

        self.events = {}
        self.extracted_events_details = []
        # Arguments for the GAN.
        self.gan_arguments = {
            "noise_dimension": 10,  # input_dim to GAN
            "output_dimension": 6,
            "hidden_dimension": 128,
            "labels_length": 3,
        }
        # FIX ME: should set to gpu if available??
        self.device = torch.device("cpu")

    @property
    def _absolute_output_path(self):
        if self.simulation is not None:
            return self.simulation.get_output_path(self.output_folder, is_file_or_directory='directory')
        else:
            return Path('.') / self.output_folder

    def get_absolute_path_to_folder(self, folder):
        p = self._absolute_output_path / folder
        os.makedirs(p, exist_ok=True)
        return p

    def initialize(self):
        # if self.simulation is None:
        #     fatal(f"The {self.type_name} needs a reference to the GATE simulation. "
        #           "Set it by 'my_optigan.simulation = ...', "
        #           f"where my_optigan is the {self.type_name} object in your script.")

        # Sub-folders (relative to output_folder
        self.optigan_input_folder = Path("optigan_inputs")
        self.optigan_output_folder = Path("optigan_outputs")
        self.optigan_csv_output_folder = self.optigan_output_folder / "csv_files"
        self.optigan_plots_folder = self.optigan_output_folder / "plots"

        # clear the input folder to make sure previous runs do not interfere
        delete_folder_contents(self.get_absolute_path_to_folder(self.optigan_input_folder))

    # Print the input info in the terminal.
    def pretty_print_events(self):
        for seq_id, event in self.events.items():
            print(f"event ID {seq_id}:")
            for particle in event:
                if particle["type"] == "gamma" or particle["type"] == "e-":
                    print(
                        f"  Particle {particle['index']}: Type={particle['type']}, Position=({particle['x']:.2f}, {particle['y']:.2f}, {particle['z']:.2f})"
                    )
                if particle["type"] == "opticalphoton":
                    print(
                        f"Total number of optical photons generated are: {particle['optical_photon_count']}"
                    )
            print()

    # Similar to above method but in a different format.
    def print_details_of_events(self):
        print(
            f"The length of extracted events details {len(self.extracted_events_details)}"
        )
        for event_id, detail in enumerate(self.extracted_events_details):
            gamma_pos = detail["gamma_position"]
            num_electrons = detail["electron_count"]
            num_optical_photons = detail["optical_photon_count"]
            print(
                f"Event ID: {event_id}, Gamma Position: {gamma_pos}, Number of Electrons: {num_electrons}, Number of Optical Photons: {num_optical_photons}"
            )
            print()

    # Save the extracted information into csv files.
    def save_optigan_inputs(self):

        print(f"The optigan input files will be saved at {self.optigan_input_folder}")

        for event_id, detail in enumerate(self.extracted_events_details):
            gamma_pos_x = detail["gamma_position"][0]
            gamma_pos_y = detail["gamma_position"][1]
            gamma_pos_z = detail["gamma_position"][2]
            num_optical_photons = detail["optical_photon_count"]

            data = {
                "gamma_pos_x": [gamma_pos_x],
                "gamma_pos_y": [gamma_pos_y],
                "gamma_pos_z": [gamma_pos_z],
                "num_optical_photons": [num_optical_photons],
            }

            # DELETE: delete this file after verification.
            pd.DataFrame(data).to_csv(self.get_absolute_path_to_folder(self.optigan_input_folder) / f"optigan_input_{event_id}.csv", index=False)

            print(
                f"Event ID: {event_id}, Gamma Position: {gamma_pos_x}, {gamma_pos_y}, {gamma_pos_z}, "
                f"Number of Optical Photons: {num_optical_photons}"
            )
            print()

    # Loads the OptiGAN model
    def create_generator(self):
        input_dim, output_dim, hidden_dim, labels_len = self.gan_arguments.values()

        # Load the saved model checkpoint.
        checkpoint = torch.load(self.path_to_optigan_model, map_location=self.device)

        # Initialize the model.
        generator = WGANGenerator(input_dim, output_dim, hidden_dim, labels_len)

        # Print model and checkpoint state_dict sizes.
        print("Model's state_dict:")
        for param_tensor in generator.state_dict():
            print(param_tensor, "\t", generator.state_dict()[param_tensor].size())

        print("\nCheckpoint's state_dict:")
        for param_tensor in checkpoint["generator_state_dict"]:
            print(
                param_tensor,
                "\t",
                checkpoint["generator_state_dict"][param_tensor].size(),
            )

        # Load the state_dict into the model.
        generator.load_state_dict(checkpoint["generator_state_dict"])

        # Move the model to the appropriate device.
        generator.to(self.device)

        # Set the model to evaluation mode.
        generator.eval()

        return generator

    # Plot graphs of OptiGAN outputs.
    # Graphs are saved in different event folders.
    def generate_and_save_optigan_graphs(self):
        csv_files = sorted(
            [
                file
                for file in os.listdir(self.optigan_csv_output_folder)
                if file.endswith(".csv")
            ],
            key=extract_number,
        )
        print(csv_files)

        for file_index, csv_file in enumerate(csv_files):
            df = pd.read_csv(self.optigan_csv_output_folder / csv_file)
            out_path = self.get_absolute_path_to_folder(self.optigan_plots_folder / f"event{file_index + 1}")

            for column in df.columns:
                plt.figure(figsize=(10, 6))
                plt.hist(df[column].dropna(), bins=30, color="blue", edgecolor="black")  # Drop NaNs for cleaner plots
                plt.title(f'{column}: Distribution for event {file_index + 1}')
                plt.xlabel(column)
                plt.ylabel('Frequency')
                # # Plot the graph using seaborn
                # plt.figure(figsize=(10, 6))
                # plt.hist(
                #     df['values'], bins='auto', color="blue", edgecolor="black"
                # )
                # plt.xlabel(column)
                # plt.ylabel("Frequency")
                # plt.title(f"{column} Distribution for Event {file_index + 1}")
                plt.tight_layout()

                # Construct the file path and save the plot
                plt.savefig(out_path / f"{column}_event_{file_index + 1}.png")
                plt.close()

            print(
                f"The graphs for the output file {csv_file} are successfully created "
                f"in {out_path}"
            )

    # Generates output of OptiGAN.
    def generate_and_save_optigan_output(self):

        # Sort and list CSV files.
        csv_files = sorted(
            [
                file
                for file in os.listdir(self.simulation.get_output_path(self.optigan_input_folder,
                                                                       is_file_or_directory='directory'))
                if file.endswith(".csv")
            ],
            key=extract_number,
        )
        print(f"The csv files in the folder are {csv_files}")

        output_path = self.get_absolute_path_to_folder(self.optigan_output_folder)
        # Clean the output folder.
        delete_folder_contents(output_path)
        print(f"The optigan output files will be saved at {output_path}")

        for file_index, file_name in enumerate(csv_files):
            # Prepare input file path and read csv.
            df = pd.read_csv(self.get_absolute_path_to_folder(self.optigan_input_folder) / file_name)

            # Extract and ensure total number of photons is a valid integer.
            total_number_of_photons = df["num_optical_photons"].values[0]
            print(f"Processing {file_name} with {total_number_of_photons} photons.")

            # Move the initial conditional values to the device.
            classX_single = torch.tensor(
                df["gamma_pos_x"].values, dtype=torch.float32
            ).to(self.device)
            classY_single = torch.tensor(
                df["gamma_pos_y"].values, dtype=torch.float32
            ).to(self.device)
            classZ_single = torch.tensor(
                df["gamma_pos_z"].values, dtype=torch.float32
            ).to(self.device)

            # Expand the conditional input vectors to match the total number of rows.
            classX = classX_single.expand(total_number_of_photons)
            classY = classY_single.expand(total_number_of_photons)
            classZ = classZ_single.expand(total_number_of_photons)

            # Create the random noise vector and combine conditions.
            noise = torch.randn(
                total_number_of_photons, self.gan_arguments["noise_dimension"]
            ).to(self.device)
            conditions = torch.stack([classX, classY, classZ], dim=1)

            # Concatenate noise and conditional input into one tensor
            generator_input = torch.cat((noise, conditions), dim=1)

            # Generate data using the model
            with torch.no_grad():
                generated_data = self.generator(generator_input)

            # Convert generated data to a DataFrame and save as a CSV file
            generated_data_np = generated_data.cpu().numpy()
            # generated_data_np = generated_data.to('cpu').detach().numpy()
            column_names = ["X", "Y", "dX", "dY", "dZ", "Ekine"]
            generated_df = pd.DataFrame(generated_data_np, columns=column_names)

            # Save the output CSV file
            optigan_output_csv_file_save_path = self.get_absolute_path_to_folder(self.optigan_csv_output_folder) / f"optigan_output_{file_index + 1}.csv"
            generated_df.to_csv(optigan_output_csv_file_save_path, index=False)
            print(f"Saved generated data to {optigan_output_csv_file_save_path}.")

    # Runs all the methods of OptiGAN
    def run_optigan(self, create_output_graphs):
        self.initialize()
        df_combined = self.get_dataframe_from_root_file()
        self.events = process_root_output_into_events(df_combined)
        self.extracted_events_details = self.extract_event_details()
        # self.pretty_print_events()
        # self.print_details_of_events()
        self.save_optigan_inputs()
        self.generator = self.create_generator()
        self.generate_and_save_optigan_output()

        if create_output_graphs:
            self.generate_and_save_optigan_graphs()

    # This is just a temporary method to get the details printed
    # without creating optigan outputs.
    def print_root_info(self):
        self.events = process_root_output_into_events()
        self.extracted_events_details = self.extract_event_details()
        # self.pretty_print_events()
        self.print_details_of_events()

    def get_dataframe_from_root_file(self):
        print(
            f"This is inside OptiganHelpers class, the root file is {self.root_file_path}"
        )
        with uproot.open(self.root_file_path) as file:
            root_tree = file["Phase"]
            print(f"The data type of the tree variable is {type(root_tree)}")
            # Save the particle co-ordinates and other information
            position_x = root_tree["Position_X"].array(library="np")
            position_y = root_tree["Position_Y"].array(library="np")
            position_z = root_tree["Position_Z"].array(library="np")
            particle_types = root_tree["ParticleName"].array(library="np")
            track_ids = root_tree["TrackID"].array(library="np")

        # Create a DataFrame from the final arrays
        df = pd.DataFrame(
            {
                "TrackID": track_ids,
                "ParticleType": particle_types,
                "Position_X": position_x,
                "Position_Y": position_y,
                "Position_Z": position_z,
            }
        )

        df["OriginalIndex"] = df.index

        # Step 1: Filter out rows where ParticleType is "opticalphoton"
        opticalphoton_df = df[df["ParticleType"] == "opticalphoton"]

        # Step 2: Drop duplicates based on TrackID, keeping the first occurrence
        opticalphoton_df_unique = opticalphoton_df.loc[
            ~opticalphoton_df.duplicated(subset="TrackID", keep="first")
        ]

        # Step 3: Filter out rows where ParticleType is NOT "opticalphoton" (e.g., "gamma")
        non_opticalphoton_df = df[df["ParticleType"] != "opticalphoton"]

        # Step 4: Concatenate both DataFrames to keep the structure intact
        df_combined = pd.concat([opticalphoton_df_unique, non_opticalphoton_df])

        # Step 5: Optionally, sort the DataFrame based on index to restore the original order if needed
        df_combined = df_combined.sort_index()

        # Save the DataFrame to a CSV file
        df_combined.to_csv(self.get_absolute_path_to_folder(self.optigan_output_folder) / "output.csv", index=False)

        return df_combined

    # This method will extract gamma, electron
    # and optical photon information from the file.
    #  (not separated by events)

    # This method will divide the extracted information
    # from above method to various events
    def extract_event_details(self):
        event_details = []
        for event_id, event in self.events.items():
            # dictionary format to store each event
            event_info = {
                "gamma_position": None,
                "electron_count": 0,
                "optical_photon_count": 0,
            }

            # loop through the particles in the event
            for particle in event:
                if particle["type"] == "gamma":
                    # save the position of the gamma particle
                    event_info["gamma_position"] = (
                        particle["x"],
                        particle["y"],
                        particle["z"],
                    )
                elif particle["type"] == "e-":
                    # increment the count of electrons
                    event_info["electron_count"] += 1
                elif particle["type"] == "opticalphoton":
                    event_info["optical_photon_count"] = particle[
                        "optical_photon_count"
                    ]

            if event_info["optical_photon_count"] != 0:
                event_details.append(event_info)

        return event_details
