import uproot

class OptiganHelpers:
    """
    Everything related to Optigan should be here
    """
    def __init__(self, root_file_path):
        self.root_file_path = root_file_path
        self.events = {}
        self.extracted_events_details = []

    def open_root_file(self):
        with uproot.open(self.root_file_path) as file:
            tree = file["Phase"]
        return tree
    
    def pretty_print_events(self):
        for seq_id, event in self.events.items():
            print(f"event ID {seq_id}:")
            for particle in event:
                if particle['type']=="gamma" or particle['type']=="e-":
                    print(f"  Particle {particle['index']}: Type={particle['type']}, Position=({particle['x']:.2f}, {particle['y']:.2f}, {particle['z']:.2f})")
                if particle['type']=="opticalphoton":
                    print(f"Total number of optical photons generated are: {particle['optical_photon_count']}")
            print()
    
    def print_details_of_events(self):
        for event_id, detail in enumerate(self.extracted_events_details):
            gamma_pos = detail['gamma_position']
            num_electrons = detail['electron_count']
            num_optical_photons = detail['optical_photon_count']
            print(f"Event ID: {event_id}, Gamma Position: {gamma_pos}, Number of Electrons: {num_electrons}, Number of Optical Photons: {num_optical_photons}")
            print()

    
    def get_optigan_input(self):
        # store all the processed events in a dictionary format
        # key: event id, value: all the particles belonging to that event
        self.events = self.process_root_output_into_events()
        self.extracted_events_details = self.extract_event_details()
        # self.pretty_print_events()
        self.print_details_of_events()
        return self.extracted_events_details
        
    def process_root_output_into_events(self):
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

            event_details.append(event_info)
        return event_details
          
        # print(f"This is for test.\nThe length of position_x, position_y, position_z, and particle_type are {len(position_x)}, {len(position_y)}, {len(position_z)}, and {len(particle_types)}")
        
        

