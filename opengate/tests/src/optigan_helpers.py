import uproot
import opengate.tests.utility as tu
import os
import shutil
import pandas as pd
import re
import seaborn as sns
import matplotlib.pyplot as plt

import torch
import math
import numpy as np

import torch.nn as nn

# FIXME: should find an alternative
# Nils told that this is only for validating test cases. 
# use direct path? 
paths = tu.get_default_test_paths(__file__, "")

def extract_number(filename):
    match = re.search(r'\d+', filename)
    if match:
        return int(match.group())
    return 0 

# Generator class architecture for 3x3x3 crystal
class WGAN_Generator(nn.Module):

    def __init__(self, input_dim, output_dim, hidden_dim, labels_len):
        super(WGAN_Generator, self).__init__()
        self.model = nn.Sequential(nn.Linear(input_dim + labels_len, hidden_dim),
                                   nn.ReLU(True),

                                   nn.Linear(hidden_dim, 2 * hidden_dim),
                                   nn.ReLU(True),

                                   nn.Linear(2 * hidden_dim, 4 * hidden_dim),
                                   nn.ReLU(True),

                                   nn.Linear(4 * hidden_dim, output_dim),
        )

    def forward(self, x):
        return self.model(x)

# all the methods that will help to extract the input info from root file 
# and save them as .csv file to give as input to optigan
class Optigan:
    """
    Everything related to Optigan should be here
    """
    def __init__(self, root_file_path):
        self.root_file_path = root_file_path
        self.events = {}
        self.extracted_events_details = []
        self.optigan_model_folder= os.path.join(paths.data, "optigan_models")
        self.gan_arguments = {}
        # setting this as "cpu" for now because 
        # other options are causing an error
        self.device = torch.device("cpu")
        # this is one model (model_3341.pt) for 3*3*3 crystal dimension
        # which we have trained and will be used as default model for now
        # in the future there might me multiple models (just like physics lists)
        # users can use their own model depending on crystal size
        self.optigan_model_file_path = os.path.join(self.optigan_model_folder, "model_3341.pt")
        self.optigan_input_folder = os.path.join(paths.data, "optigan_inputs")
        self.optigan_output_folder = os.path.join(paths.data, "optigan_outputs")
        self.optigan_csv_output_folder = os.path.join(self.optigan_output_folder, "csv_files")
        self.optigan_output_graphs_folder = os.path.join(self.optigan_output_folder, "graphs")

    # opens root file and return the phase info 
    def open_root_file(self):
        file = uproot.open(self.root_file_path)
        tree = file["Phase"]
        print(f"The data type of the tree variable is {type(tree)}")
        return file, tree
    
    # this will print the input info in the terminal
    def pretty_print_events(self):
        for seq_id, event in self.events.items():
            print(f"event ID {seq_id}:")
            for particle in event:
                if particle['type']=="gamma" or particle['type']=="e-":
                    print(f"  Particle {particle['index']}: Type={particle['type']}, Position=({particle['x']:.2f}, {particle['y']:.2f}, {particle['z']:.2f})")
                if particle['type']=="opticalphoton":
                    print(f"Total number of optical photons generated are: {particle['optical_photon_count']}")
            print()

    # similar to above method, just a format difference
    def print_details_of_events(self):
        print(f"The length of extracted events details {len(self.extracted_events_details)}")
        for event_id, detail in enumerate(self.extracted_events_details):
            gamma_pos = detail['gamma_position']
            num_electrons = detail['electron_count']
            num_optical_photons = detail['optical_photon_count']
            print(f"Event ID: {event_id}, Gamma Position: {gamma_pos}, Number of Electrons: {num_electrons}, Number of Optical Photons: {num_optical_photons}")
            print()
    
    # this method will save the extracted information into csv files
    def save_optigan_inputs(self):
        # check if the folder exists
        if os.path.exists(self.optigan_input_folder):
            # delete all files in the folder
            shutil.rmtree(self.optigan_input_folder)
        
        os.makedirs(self.optigan_input_folder)
        
        print(f"The optigan input files will be saved at {self.optigan_input_folder}")

        for event_id, detail in enumerate(self.extracted_events_details):
            gamma_pos_x = detail['gamma_position'][0]
            gamma_pos_y = detail['gamma_position'][1]
            gamma_pos_z = detail['gamma_position'][2]
            num_optical_photons = detail['optical_photon_count']

            filename = f"optigan_input_{event_id}.csv"
            filepath = os.path.join(self.optigan_input_folder, filename)

            data = {
                "gamma_pos_x": [gamma_pos_x],
                "gamma_pos_y": [gamma_pos_y],
                "gamma_pos_z": [gamma_pos_z],
                "num_optical_photons": [num_optical_photons]
            }

            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)

            print(f"Event ID: {event_id}, Gamma Position: {gamma_pos_x}, {gamma_pos_y}, {gamma_pos_z}, Number of Optical Photons: {num_optical_photons}")
            print()

    def load_gan_model(self):

        self.gan_arguments = {
            "noise_dimension": 10,
            "output_dimension": 6,
            "hidden_dimension": 128,
            "labels_length" : 3
        }

        # Define your model dimensions
        noise_dimension = 10
        output_dimension = 6
        hidden_dimension = 128
        labels_length = 3

        # Load the saved model checkpoint
        checkpoint = torch.load(self.optigan_model_file_path, map_location = self.device)

        # Initialize the model 
        generator = WGAN_Generator(noise_dimension, output_dimension, hidden_dimension, labels_length)

        # Print model and checkpoint state_dict sizes
        print("Model's state_dict:")
        for param_tensor in generator.state_dict():
            print(param_tensor, "\t", generator.state_dict()[param_tensor].size())

        print("\nCheckpoint's state_dict:")
        for param_tensor in checkpoint['generator_state_dict']:
            print(param_tensor, "\t", checkpoint['generator_state_dict'][param_tensor].size())

        # Load the state_dict into the model
        generator.load_state_dict(checkpoint['generator_state_dict'])

        # Move the model to the appropriate device
        generator.to(self.device)

        # Set the model to evaluation mode
        generator.eval()

        return generator
    
    def get_optigan_graphs(self): 
        csv_files = sorted([file for file in os.listdir(self.optigan_csv_output_folder) if file.endswith('.csv')], key = extract_number)
        print(csv_files)

        for file_index, csv_file in enumerate(csv_files):
            csv_file_path = os.path.join(self.optigan_csv_output_folder, csv_file)
            df = pd.read_csv(csv_file_path)

            column_names  = df.columns.tolist() # redundant? 

            for column in column_names:
                # Define the sub-directory path where each event graph will be stored
                optigan_output_graph_file_save_path = os.path.join(self.optigan_output_graphs_folder, f"event{file_index + 1}")

                # Create the directory if it doesn't exist
                os.makedirs(optigan_output_graph_file_save_path, exist_ok=True)

                # Plot the graph using seaborn
                plt.figure(figsize=(10, 6))
                sns.histplot(data=df, x=column, bins=30, color="blue", edgecolor="black")
                plt.xlabel(column)
                plt.ylabel("Frequency")
                plt.title(f"{column} Distribution for Event {file_index + 1}")
                plt.tight_layout()

                # Construct the file path and save the plot
                graph_path = os.path.join(optigan_output_graph_file_save_path, f"{column}_event_{file_index + 1}.png")
                plt.savefig(graph_path)
                plt.close()
            
            print(f"The graphs for the output file {csv_file} are succesfully created in {optigan_output_graph_file_save_path} folder")




    # Loads the model with pre-trained weights and generates output of optigan
    def get_optigan_outputs(self):

        # Sort and list CSV files
        csv_files = sorted([file for file in os.listdir(self.optigan_input_folder) if file.endswith('.csv')], key = extract_number)
        print(f"The csv files in the folder are {csv_files}")

        # Clean and recreate the output folder
        if os.path.exists(self.optigan_output_folder):
            shutil.rmtree(self.optigan_output_folder)
        os.makedirs(self.optigan_output_folder)
        print(f"The optigan output files will be saved at {self.optigan_output_folder}")

        for file_index, file_name in enumerate(csv_files):

            # Prepare input file path and read csv
            csv_file_path = os.path.join(self.optigan_input_folder, file_name)
            df = pd.read_csv(csv_file_path)

            # Extract and ensure total number of photons is a valid integer
            total_number_of_photons = df["num_optical_photons"].values[0]
            print(f"Processing {file_name} with {total_number_of_photons} photons.")

            # Move the initial conditional values to the device
            classX_single = torch.tensor(df["gamma_pos_x"].values, dtype=torch.float32).to(self.device)
            classY_single = torch.tensor(df["gamma_pos_y"].values, dtype=torch.float32).to(self.device)
            classZ_single = torch.tensor(df["gamma_pos_z"].values, dtype=torch.float32).to(self.device)

            # Expand the conditional input vectors to match the total number of rows
            classX = classX_single.expand(total_number_of_photons)
            classY = classY_single.expand(total_number_of_photons)
            classZ = classZ_single.expand(total_number_of_photons)

            # Create the random noise vector and combine conditions
            noise = torch.randn(total_number_of_photons, self.gan_arguments["noise_dimension"]).to(self.device)
            conditions = torch.stack([classX, classY, classZ], dim=1)

            # Concatenate noise and conditional input into one tensor
            generator_input = torch.cat((noise, conditions), dim=1)

            # Generate data using the model
            with torch.no_grad():
                generated_data = self.generator(generator_input)
            
            # Convert generated data to a DataFrame and save as a CSV file
            generated_data_np = generated_data.cpu().numpy()
            # generated_data_np = generated_data.to('cpu').detach().numpy()
            column_names = ['X', 'Y', 'dX', 'dY', 'dZ', 'Ekine']
            generated_df = pd.DataFrame(generated_data_np, columns=column_names)

            # Save the output CSV file
            optigan_output_csv_file_save_path = os.path.join(self.optigan_csv_output_folder, f"optigan_output_{file_index + 1}.csv")
            os.makedirs(os.path.dirname(optigan_output_csv_file_save_path), exist_ok=True)
            generated_df.to_csv(optigan_output_csv_file_save_path, index=False)
            print(f"Saved generated data to {optigan_output_csv_file_save_path}.")

        # # Plot histograms using Seaborn for each column
        #     for column in column_names:
        #         # Define the sub-directory path where each event graph will be stored
        #         optigan_output_graph_file_save_path = os.path.join(self.optigan_output_graphs_folder, f"event{file_index + 1}")

        #         # Create the directory if it doesn't exist
        #         os.makedirs(optigan_output_graph_file_save_path, exist_ok=True)

        #         # Plot the graph using seaborn
        #         plt.figure(figsize=(10, 6))
        #         sns.histplot(data=generated_df, x=column, bins=30, kde=True, color="blue", edgecolor="black")
        #         plt.xlabel(column)
        #         plt.ylabel("Frequency")
        #         plt.title(f"{column} Distribution for Event {file_index + 1}")
        #         plt.tight_layout()

        #         # Construct the file path and save the plot
        #         graph_path = os.path.join(optigan_output_graph_file_save_path, f"{column}_event_{file_index + 1}.png")
        #         plt.savefig(graph_path)
        #         plt.close()

        #     # Create a single figure containing all columns
        #     # Create a grid layout (e.g., 2 rows, 3 columns)
        #     num_columns = len(column_names)
        #     num_cols_per_row = 3
        #     num_rows = math.ceil(num_columns / num_cols_per_row)

        #     fig, axs = plt.subplots(nrows=num_rows, ncols=num_cols_per_row, figsize=(18, 10))
        #     fig.suptitle(f"All Graphs for Event {file_index + 1}")

        #     for i, column in enumerate(column_names):
        #         row = i // num_cols_per_row
        #         col = i % num_cols_per_row
        #         sns.histplot(data=generated_df, x=column, bins=30, kde=True, color="blue", edgecolor="black", ax=axs[row][col])
        #         axs[row][col].set_xlabel(column)
        #         axs[row][col].set_ylabel("Frequency")
        #         axs[row][col].set_title(f"{column} Distribution")

        #     # If there are empty subplots, hide them
        #     for i in range(num_columns, num_rows * num_cols_per_row):
        #         row = i // num_cols_per_row
        #         col = i % num_cols_per_row
        #         fig.delaxes(axs[row][col])

        #     plt.tight_layout(rect=[0, 0, 1, 0.96])
        #     all_graphs_path = os.path.join(optigan_output_graph_file_save_path, f"all_graphs_{file_index + 1}.png")
        #     plt.savefig(all_graphs_path)
        #     plt.close()

    # this method is called from engines.py and takes care of 
    # running all other methods. 
    def run_optigan(self):
        # store all the processed events in a dictionary format
        # key: event id, value: all the particles belonging to that event
        self.events = self.process_root_output_into_events()
        self.extracted_events_details = self.extract_event_details()
        # self.pretty_print_events()
        # self.print_details_of_events()
        self.save_optigan_inputs()
        self.generator = self.load_gan_model()
        self.get_optigan_outputs()
        self.get_optigan_graphs()
    
    def print_root_info(self):
        self.events = self.process_root_output_into_events()
        self.extracted_events_details = self.extract_event_details()
        # self.pretty_print_events()
        self.print_details_of_events()
            
    # this method will take the root file and extract gamma, electron
    # and optical photon information from the file. 
    def process_root_output_into_events(self):
        print(f"This is inside OptiganHelpers class, the root file is {self.root_file_path}")
        file, root_tree = self.open_root_file()

        # save the particle co-ordinates and other information
        position_x = root_tree["Position_X"].array(library="np")
        position_y = root_tree["Position_Y"].array(library="np")
        position_z = root_tree["Position_Z"].array(library="np")
        particle_types = root_tree["ParticleName"].array(library="np")
        track_ids = root_tree["TrackID"].array(library="np")

        file.close()

        # Create a DataFrame from the final arrays
        df = pd.DataFrame({
            "TrackID": track_ids,
            "ParticleType": particle_types,
            "Position_X": position_x,
            "Position_Y": position_y,
            "Position_Z": position_z
        })

        df['OriginalIndex'] = df.index

        # Step 1: Filter out rows where ParticleType is "opticalphoton"
        opticalphoton_df = df[df["ParticleType"] == "opticalphoton"]

        # Step 2: Drop duplicates based on TrackID, keeping the first occurrence
        opticalphoton_df_unique = opticalphoton_df.loc[~opticalphoton_df.duplicated(subset="TrackID", keep="first")]

        # Step 3: Filter out rows where ParticleType is NOT "opticalphoton" (e.g., "gamma")
        non_opticalphoton_df = df[df["ParticleType"] != "opticalphoton"]

        # Step 4: Concatenate both DataFrames to keep the structure intact
        df_combined = pd.concat([opticalphoton_df_unique, non_opticalphoton_df])

        # Step 5: Optionally, sort the DataFrame based on index to restore the original order if needed
        df_combined = df_combined.sort_index()

        position_x = df_combined["Position_X"].to_numpy()
        position_y = df_combined["Position_Y"].to_numpy()
        position_z = df_combined["Position_Z"].to_numpy()
        particle_types =  df_combined["ParticleType"].to_numpy()
                
        # Save the DataFrame to a CSV file
        df_combined.to_csv("output.csv", index=False)

        # variables
        events = {} # will store all the events 
        current_event = []
        event_id = 0

        # flag to check if gamma is followed by electrons or photons
        gamma_has_electrons_or_photons = False

        # counts the occurence of optical photons in current event
        optical_photon_count = 0

        # process each particle and segregate into events
        for index, (ptype, x, y, z) in enumerate(zip(particle_types, position_x, position_y, position_z)):
            if ptype == "gamma":
                # store the previous event if it started with a gamma
                # and is followed by electrons or photons
                if current_event and gamma_has_electrons_or_photons:
                    current_event.append({'type': "opticalphoton", 'optical_photon_count': optical_photon_count})
                    # print(f"The optical photon count is {optical_photon_count}")
                    events[event_id] = current_event
                    event_id += 1
                    optical_photon_count = 0
                # if it is a new event, add the gamma particle to it
                current_event = [{'index': index, 'type': ptype, 'x':x, 'y':y, 'z': z}]
                gamma_has_electrons_or_photons = False
            elif ptype == "opticalphoton":
                # if the particle is optical photon, just increment the count
                optical_photon_count += 1
                gamma_has_electrons_or_photons = True
            elif ptype == "e-":
                # Only add e- if there is an ongoing event (started by gamma)
                if current_event:
                    current_event.append({'index': index, 'type': ptype, 'x': x, 'y': y, 'z': z})
                    gamma_has_electrons_or_photons = True

        # print(f"Outside the for loop, the optical photon count is {optical_photon_count}")

        # Store the last event if it is not empty
        if len(current_event) > 1:
            current_event.append({'type': "opticalphoton", 'optical_photon_count': optical_photon_count})
            events[event_id] = current_event

        # print(f"The length of events is {len(events)}") # debugging

        return events
    
    # this method will divide the extracted information 
    # from above method to various events
    def extract_event_details(self):
        event_details = []
        for event_id, event in self.events.items():
            # dictionary format to store each event
            event_info = {
                'gamma_position': None,
                'electron_count': 0,
                'optical_photon_count': 0
            }

            # loop through the particles in the event
            for particle in event:
                if particle['type'] == 'gamma':
                    # save the position of the gamma particle
                    event_info['gamma_position'] = (particle['x'], particle['y'], particle['z'])
                elif particle['type'] == 'e-':
                    # increment the count of electrons
                    # FIX_ME: maybe implement this in process_roo_output func
                    event_info['electron_count'] += 1
                elif particle['type'] == "opticalphoton":
                    event_info['optical_photon_count'] = particle['optical_photon_count'] 

            if event_info['optical_photon_count'] != 0:
                event_details.append(event_info)

        return event_details
          
        # print(f"This is for test.\nThe length of position_x, position_y, position_z, and particle_type are {len(position_x)}, {len(position_y)}, {len(position_z)}, and {len(particle_types)}")
        
        

