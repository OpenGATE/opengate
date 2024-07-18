# This file reads the data from the root file 
# and prints it in the terminal 

import opengate as gate 
import opengate.tests.utility as tu
import uproot 
import os
import pandas as pd

def process_root_file(file_path):
    # Open the ROOT file
    with uproot.open(file_path) as file:
        # Access the tree (replace 'tree_name' with your tree's name)
        tree = file["Phase"]

        # # Read particle data
        # print("Branches available in the tree:")
        # for branch_name in tree.keys():
        #     print(branch_name)

        position_x = tree["Position_X"].array(library="np")
        position_y = tree["Position_Y"].array(library="np")
        position_z = tree["Position_Z"].array(library="np")
        particle_types = tree["ParticleName"].array(library="np")

        # Initialize variables
        events = {}
        current_event = []
        event_id = 0
        gamma_has_electrons_or_photons = False # Flag to check if gamma is followed by electrons
        optical_photon_count = 0

        # Process each particle to form events
        for index, (ptype, x, y, z) in enumerate(zip(particle_types, position_x, position_y, position_z)):
            if ptype == "gamma":
                # Store the previous event if it started with a gamma that had electrons
                if current_event and gamma_has_electrons_or_photons:
                    current_event.append({'type': "opticalphoton", 'optical_photon_count': optical_photon_count})
                    events[event_id] = current_event
                    event_id += 1
                    optical_photon_count = 0
                current_event = [{'index': index, 'type': ptype, 'x': x, 'y':y, 'z': z}] # Start a new event
                gamma_has_electrons_or_photons = False
            elif ptype == "opticalphoton":
                optical_photon_count += 1
                gamma_has_electrons_or_photons = True
            elif ptype == "e-":
                if current_event: # Only add e- if there's an ongoing event (started by a gamma)
                    current_event.append({'index': index, 'type': ptype, 'x': x, 'y': y, 'z': z})
                    gamma_has_electrons_or_photons = True

        # Store the last event if no empty 
        if len(current_event) > 1:
            events[event_id] = current_event

    return events    

def extract_event_details(events):
    event_details = []
    for event_id, event in events.items():
        # Initialise the dictionary for each event
        event_info = {
            'gamma_position': None,
            'electron_count': 0,
            'optical_photon_count':0
        }

        # Loop through particles in the event
        for particle in event:
            if particle['type'] == 'gamma':
                # Save the position of the gamma particle
                event_info['gamma_position'] = (particle['x'], particle['y'], particle['z'])
            elif particle['type'] == 'e-':
                # Increment the count of electrons
                event_info['electron_count'] += 1
            elif particle['type'] == "opticalphoton":
                event_info['optical_photon_count'] = particle['optical_photon_count']



        # Append the information of this event to the list
        event_details.append(event_info)

    return event_details

def pretty_print_events(events):
    for seq_id, event in events.items():
        print(f"event ID {seq_id}:")
        for particle in event:
            if particle['type']=="gamma" or particle['type']=="e-":
                print(f"  Particle {particle['index']}: Type={particle['type']}, Position=({particle['x']:.2f}, {particle['y']:.2f}, {particle['z']:.2f})")
            if particle['type']=="opticalphoton":
                print(f"Total number of optical photons generated are: {particle['optical_photon_count']}")
        print()  # Print a newline for better separation between events

if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, "")
    file_path = paths.output / "test074_optigan_phsp_and_kill_actor.root"
    # print(file_path)

    # Process the ROOT file to get events
    events = process_root_file(file_path)

    # Extract details for each event
    event_details = extract_event_details(events)

    pretty_print_events(events)

    print("Input to OptiGAN")
    print()

    # Print the details of each event
    for event_id, detail in enumerate(event_details):
        gamma_pos = detail['gamma_position']
        num_electrons = detail['electron_count']
        num_optical_photons = detail['optical_photon_count']
        print(f"Event ID: {event_id}, Gamma Position: {gamma_pos}, Number of Electrons: {num_electrons}, Number of Optical Photons: {num_optical_photons}")
        print()

    # print(events[2][0])


