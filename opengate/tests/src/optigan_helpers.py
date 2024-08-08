import uproot
import opengate.tests.utility as tu
import os
import shutil
import pandas as pd
import re

import torch
import torch.nn as nn

paths = tu.get_default_test_paths(__file__, "")

def extract_number(filename):
    match = re.search(r'\d+', filename)
    if match:
        return int(match.group())
    return 0 

# still in works - can ignore this class for now
# this will be useful to load the model weights into the architecture
# and run the model to get outputs
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
class OptiganHelpers:
    """
    Everything related to Optigan should be here
    """
    def __init__(self, root_file_path):
        self.root_file_path = root_file_path
        self.events = {}
        self.extracted_events_details = []
        self.optigan_model_folder= os.path.join(paths.data, "optigan_models")
        # this is one model (model_3341.pt) for 3*3*3 crystal dimension
        # which we have trained and will be used as default model for now
        # in the future there might me multiple models (just like physics lists)
        # users can use their own model depending on crystal architecture
        self.optigan_model_file_path = os.path.join(self.optigan_model_folder, "model_3341.pt")
        self.optigan_input_folder = os.path.join(paths.data, "optigan_inputs")
        self.optigan_output_folder = os.path.join(paths.data, "optigan_outputs")

    # opens root file and return the phase info 
    def open_root_file(self):
        with uproot.open(self.root_file_path) as file:
            print("Available keys in the file:", file.keys())
            tree = file["Phase"]
        return tree
    
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
        for event_id, detail in enumerate(self.extracted_events_details):
            gamma_pos = detail['gamma_position']
            num_electrons = detail['electron_count']
            num_optical_photons = detail['optical_photon_count']
            print(f"Event ID: {event_id}, Gamma Position: {gamma_pos}, Number of Electrons: {num_electrons}, Number of Optical Photons: {num_optical_photons}")
            print()
    
    # this method will save the extracted information into csv files
    def save_optigan_inputs(self):
        print("We are inside save_optigan_inputs function")

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

    # STILL IN WORKS, this method will load the model and geenrate output of optigan
    def get_optigan_outputs(self):
        print(f"We are inside get_optigan_outputs function")

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        noise_dimension = 10
        output_dimension = 6
        hidden_dimension = 128
        labels_length = 3


        # check if the folder exists 
        if os.path.exists(self.optigan_output_folder):
            # delete all the files in the folder
            shutil.rmtree(self.optigan_output_folder)
        
        os.makedirs(self.optigan_output_folder)

        print(f"The optigan output files will be saved at {self.optigan_output_folder}")

        csv_files = sorted([file for file in os.listdir(self.optigan_input_folder) if file.endswith('.csv')], key = extract_number)

        print(f"The csv files in the folder are {csv_files}")

        # load the saved model checkpoints
        checkpoint = torch.load(self.optigan_model_file_path, map_location = device)
        # print(f"The checkpoint information is {checkpoints}")

        # load the model 
        generator = WGAN_Generator(noise_dimension, output_dimension, hidden_dimension, labels_length)

        print("Model's state_dict:")
        for param_tensor in generator.state_dict():
            print(param_tensor, "\t", generator.state_dict()[param_tensor].size())

        print("\nCheckpoint's state_dict:")
        for param_tensor in checkpoint['generator_state_dict']:
            print(param_tensor, "\t", checkpoint['generator_state_dict'][param_tensor].size())

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
        self.get_optigan_outputs()
            
    # this method will take the root file and extract gamma, electron
    # and optical photon information from the file. 
    def process_root_output_into_events(self):
        print(f"This is inside OptiganHelpers class, the root file is {self.root_file_path}")
        root_tree = self.open_root_file()

        # save the particle co-ordinates and other information
        position_x = root_tree["Position_X"].array(library="np")
        position_y = root_tree["Position_Y"].array(library="np")
        position_z = root_tree["Position_Z"].array(library="np")
        particle_types = root_tree["ParticleName"].array(library="np")

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
        
        # Store the last event if it is not empty
        if len(current_event) > 1:
            events[event_id] = current_event
    
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
        
        

