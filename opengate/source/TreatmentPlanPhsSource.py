import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate
from .TreatmentPlanSource import *
import os
import pathlib
import uproot
from pathlib import Path


class TreatmentPlanPhsSource(TreatmentPlanSource):
    def __init__(self, name, sim):
        self.name = name
        # self.mother = None
        self.rotation = Rotation.identity()
        self.translation = [0, 0, 0]
        self.spots = None
        # self.path_to_phaseSpaceFiles = ""
        self.phaseSpaceList_file_name = ""
        self.phaseSpaceList = {}
        self.n_sim = 0
        self.sim = sim  # simulation obj to which we want to add the tpPhS source
        self.distance_source_to_isocenter = None
        # SMX to Isocenter distance
        self.distance_stearmag_to_isocenter_x = None
        # SMY to Isocenter distance
        self.distance_stearmag_to_isocenter_y = None
        self.batch_size = None

    def __del__(self):
        pass

    def set_particles_to_simulate(self, n_sim):
        self.n_sim = n_sim

    def set_distance_source_to_isocenter(self, distance):
        self.distance_source_to_isocenter = distance

    def set_distance_stearmag_to_isocenter(self, distance_x, distance_y):
        self.distance_stearmag_to_isocenter_x = distance_x
        self.distance_stearmag_to_isocenter_y = distance_y

    def set_spots(self, spots):
        self.spots = spots

    def set_spots_from_rtplan(self, rt_plan_path):
        beamset = gate.beamset_info(rt_plan_path)
        gantry_angle = beamset.beam_angles[0]
        spots = gate.get_spots_from_beamset(beamset)
        self.spots = spots
        self.rotation = Rotation.from_euler("z", gantry_angle, degrees=True)

    def set_phaseSpaceList_file_name(self, file_name):
        self.phaseSpaceList_file_name = file_name

    def initialize_tpsource(self):
        if self.batch_size is None:
            self.batch_size = 30000
        # verify that all necessary parameters are set
        self.verify_necessary_parameters_are_set()

        # read in the phase space list
        self.phaseSpaceList = self.read_list_of_Phs(self.phaseSpaceList_file_name)
        # verify the phase space list
        self.verify_phs_files_exist(self.phaseSpaceList)

        spots_array = self.spots
        sim = self.sim
        nSim = self.n_sim

        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        cal_proportion_factor = (
            lambda d_magnet_iso: 1
            if (d_magnet_iso == float("inf"))
            else (d_magnet_iso - self.distance_source_to_isocenter) / d_magnet_iso
        )
        self.proportion_factor_x = cal_proportion_factor(
            self.distance_stearmag_to_isocenter_x
        )
        self.proportion_factor_y = cal_proportion_factor(
            self.distance_stearmag_to_isocenter_y
        )
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

            # use the local positions in phase space file
            source.position_key = "PrePositionLocal"
            source.direction_key = "PreDirectionLocal"
            if self.batch_size is not None:
                source.batch_size = self.batch_size
            else:
                source.batch_size = 30000

            source.particle = spot.particle_name

            # # set mother
            # if self.mother is not None:
            #     source.mother = self.mother

            # POSITION:
            source.override_position = True
            source.position.translation = self._get_pbs_position(spot)

            # ROTATION:
            source.override_direction = True
            source.position.rotation = self._get_pbs_rotation(spot)

            # add weight
            # source.weight = -1
            source.n = nspot

        self.actual_sim_particles = tot_sim_particles

    def _get_pbs_position(self, spot):
        # (x,y) referr to isocenter plane.
        # Need to be corrected to referr to nozzle plane
        pos = [
            (spot.xiec) * self.proportion_factor_x,
            (spot.yiec) * self.proportion_factor_y,
            self.distance_source_to_isocenter,
        ]
        # Gantry angle = 0 -> source comes from +y and is positioned along negative side of y-axis
        # https://opengate.readthedocs.io/en/latest/source_and_particle_management.html

        position = (self.rotation * Rotation.from_euler("x", np.pi / 2)).apply(
            pos
        ) + self.translation

        return position

    def _get_pbs_rotation(self, spot):
        # by default the source points in direction z+.
        # Need to account for SM direction deviation and rotation thoward isocenter (270 deg around x)
        # then rotate of gantry angle
        rotation = [0.0, 0.0, 0.0]
        beta = np.arctan(spot.yiec / self.distance_stearmag_to_isocenter_y)
        alpha = np.arctan(spot.xiec / self.distance_stearmag_to_isocenter_x)
        rotation[0] = -np.pi / 2 + beta
        rotation[2] = -alpha

        # apply gantry angle
        spot_rotation = (
            self.rotation * Rotation.from_euler("xyz", rotation)
        ).as_matrix()

        return spot_rotation

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
            print("phs_dict read: ", phs_dict)
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
