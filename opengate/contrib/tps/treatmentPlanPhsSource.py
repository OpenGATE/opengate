from scipy.spatial.transform import Rotation
import opengate_core
from opengate.contrib.tps.ionbeamtherapy import *
import os


class TreatmentPlanPhsSource(TreatmentPlanSource):

    def __init__(self, name, sim):
        super().__init__(name, sim)
        self.name = name
        self.rotation = Rotation.identity()
        self.translation = [0, 0, 0]
        self.spots = None
        self.phaseSpaceFolder = ""
        self.phaseSpaceList_file_name = ""
        self.phaseSpaceList = {}
        self.position_key_x = "PrePositionLocal_X"
        self.position_key_y = "PrePositionLocal_Y"
        self.position_key_z = "PrePositionLocal_Z"
        self.direction_key_x = "PreDirectionLocal_X"
        self.direction_key_y = "PreDirectionLocal_Y"
        self.direction_key_z = "PreDirectionLocal_Z"
        self.rotate_PhS_Source = Rotation.identity()
        self.energy_key = "KineticEnergy"
        self.weight_key = "Weight"
        self.PDGCode_key = "PDGCode"
        self.generate_until_next_primary = False
        self.primary_lower_energy_threshold = 0
        self.primary_PDGCode = 0
        self.n_sim = 0
        self.sim = sim  # simulation obj to which we want to add the tpPhS source
        self.distance_source_to_isocenter = None
        # SMX to Isocenter distance
        self.distance_stearmag_to_isocenter_x = None
        # SMY to Isocenter distance
        self.distance_stearmag_to_isocenter_y = None
        self.batch_size = None
        self.entry_start = None

    def __del__(self):
        pass

    def set_distance_source_to_isocenter(self, distance):
        self.distance_source_to_isocenter = distance
        self.d_nozzle_to_iso = distance

    def set_distance_stearmag_to_isocenter(self, distance_x, distance_y):
        self.d_stearMag_to_iso_x = distance_x
        self.d_stearMag_to_iso_y = distance_y
        self.distance_stearmag_to_isocenter_x = distance_x
        self.distance_stearmag_to_isocenter_y = distance_y

    def set_phaseSpaceList_file_name(self, file_name):
        self.phaseSpaceList_file_name = str(file_name)

    def set_phaseSpaceFolder(self, folder_name):
        self.phaseSpaceFolder = str(folder_name)

    def initialize_tpPhssource(self):
        if self.batch_size is None:
            self.batch_size = 30000
        # verify that all necessary parameters are set
        self.verify_necessary_parameters_are_set()
        # read in the phase space list
        self.phaseSpaceList = self.read_list_of_Phs(
            self.phaseSpaceList_file_name, self.phaseSpaceFolder
        )
        # verify the phase space list
        self.verify_phs_files_exist(self.phaseSpaceList)
        spots_array = self.spots
        sim = self.sim
        nSim = self.n_sim

        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        cal_proportion_factor = lambda d_magnet_iso: (
            1
            if (d_magnet_iso == float("inf"))
            else (d_magnet_iso - self.d_nozzle_to_iso) / d_magnet_iso
        )
        self.proportion_factor_x = cal_proportion_factor(self.d_stearMag_to_iso_x)
        self.proportion_factor_y = cal_proportion_factor(self.d_stearMag_to_iso_y)

        tot_sim_particles = 0
        # initialize a pencil beam for each spot
        for i, spot in enumerate(spots_array):
            # simulate a fraction of the beam particles for this spot
            nspot = np.round(spot.beamFraction * nSim)
            if nspot == 0:
                continue
            tot_sim_particles += nspot
            # create a source
            source = sim.add_source("PhaseSpaceSource", f"{self.name}_spot_{i}")

            # set energy
            # find corresponding phase space file
            if self.phaseSpaceList.get(spot.energy) is not None:
                source.phsp_file = self.phaseSpaceList.get(spot.energy)
            else:
                print(
                    "ERROR in TreatmentPlanPhsSource: Energy requested from plan file does not exist. Aborting."
                )
                print("Requested energy was: ", spot.energy)
                exit(-1)

            # set keys of phase space file to use
            source.position_key_x = self.position_key_x
            source.position_key_y = self.position_key_y
            source.position_key_z = self.position_key_z
            source.direction_key_x = self.direction_key_x
            source.direction_key_y = self.direction_key_y
            source.direction_key_z = self.direction_key_z
            source.energy_key = self.energy_key
            source.weight_key = self.weight_key
            source.PDGCode_key = self.PDGCode_key

            if self.batch_size is not None:
                source.batch_size = self.batch_size
            else:
                source.batch_size = 30000

            # if not set, initialize the entry_start to 0 or to a list for multithreading
            if self.entry_start is None:
                if not opengate_core.IsMultithreadedApplication():
                    self.entry_start = 0
                else:
                    # create a entry_start array with the correct number of start entries
                    # all entries are spaced by the number of particles/thread
                    n_threads = self.simulation.user_info.number_of_threads
                    # ui.entry_start = [0] * n_threads
                    step = np.ceil(nspot / n_threads) + 1  # Specify the increment value
                    self.entry_start = [i * step for i in range(n_threads)]
                print(
                    "INFO: entry_start not set. Using default values: ",
                    self.entry_start,
                )

            source.entry_start = self.entry_start

            # POSITION:
            source.translate_position = True
            source.position.translation = self._get_pbs_position(spot)
            # print("source.position.translation: ", source.position.translation)

            # ROTATION:
            source.rotate_direction = True
            # # use pbs rotation plus a potential rotation of the original phs
            # # may be necessary in case the original phs is not going into +z direction
            source.position.rotation = (
                self._get_pbs_rotation(spot) @ self.rotate_PhS_Source.as_matrix()
            )

            # add weight
            source.n = nspot

            # allow the possibility to count primaries
            source.generate_until_next_primary = self.generate_until_next_primary
            source.primary_lower_energy_threshold = self.primary_lower_energy_threshold
            source.primary_PDGCode = self.primary_PDGCode

        self.actual_sim_particles = tot_sim_particles

    def verify_phs_files_exist(self, phs_dict):
        """Check if all the files in the dictionary exist.
        Returns True if all the files exist, False otherwise
        If one file does not exist, the program is aborted."""

        for key, phs_file in phs_dict.items():
            # print(
            #     "key: ",
            #     key,
            #     " phs_file: ",
            #     phs_file,
            #     " type: ",
            #     type(phs_file),
            # )

            if not os.path.isfile(phs_file):
                print(
                    "ERROR in ThreatmenPlanPhsSource: File {} does not exist".format(
                        phs_file
                    )
                )
                print("Error: File in Phase space dictionary does not exist. Aborting.")
                exit(-1)
        return True

    def read_list_of_Phs(self, file_name: str, path_to_phsp=""):
        """Read a list of Phs from a file.

        Parameters
        ----------
        file_name : str
            The name of the file to read from.
            File needs to have at least two columns
            First column is the energy in MeV which is the energy label
            Second column is the phase space file name
        Returns
        -------
        dictionary of Phs"""

        # prepend the path to the phase space files
        file_name = path_to_phsp + "/" + file_name

        phs_dict = {}
        try:
            input_arr = np.genfromtxt(
                file_name,
                delimiter="\t",
                comments="#",
                usecols=(0, 1),
                dtype=None,
                encoding=None,
            )

            # convert to dictionary
            if input_arr.shape == (0,):
                print(
                    "Error in TreatmentPlanPhsSource: No data found in file: ",
                    file_name,
                    " Aborting.",
                )
                exit(-1)
            if input_arr.ndim == 0:
                # only single line read, convert to array
                input_arr = np.array([input_arr])

            # normal case, multiple lines
            if path_to_phsp != "":
                phs_dict = {
                    float(i[0]): str(path_to_phsp + "/" + (i[1])) for i in input_arr
                }
            else:
                phs_dict = {float(i[0]): str(i[1]) for i in input_arr}
            # print("phs_dict read: ", phs_dict)
        except Exception as e:
            print(
                "Error in TreatmentPlanPhsSource: could not read the phase space file list. Aborting."
            )
            print("The error was: ", e)
            exit(-1)
        if len(phs_dict) == 0:
            print(
                "Error in TreatmentPlanPhsSource: the phase space file list is empty. Aborting."
            )
            exit(-1)
        return phs_dict

    def verify_necessary_parameters_are_set(self):
        """This function checks whether all necessary parameters were set.
        E.g. not None
        It does not check sensibility"""
        if self.phaseSpaceList_file_name is None:
            print(
                "Error in TreatmentPlanPhsSource: phaseSpaceList_file_name is None. Aborting."
            )
            exit(-1)
        if self.distance_source_to_isocenter is None:
            print(
                "Error in TreatmentPlanPhsSource: distance_source_to_isocenter is None. Aborting."
            )
            exit(-1)
        if self.distance_stearmag_to_isocenter_x is None:
            print(
                "Error in TreatmentPlanPhsSource: distance_stearmag_to_isocenter_x is None. Aborting."
            )
            exit(-1)
        if self.distance_stearmag_to_isocenter_y is None:
            print(
                "Error in TreatmentPlanPhsSource: distance_stearmag_to_isocenter_y is None. Aborting."
            )
            exit(-1)
        if self.batch_size is None:
            print("Error in TreatmentPlanPhsSource: batch_size is None. Aborting.")
            exit(-1)
        if self.spots is None:
            print("Error in TreatmentPlanPhsSource: No spots have been set. Aborting.")
            exit(-1)
