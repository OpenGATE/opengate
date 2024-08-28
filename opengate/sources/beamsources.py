import math
from box import Box
import numpy as np
from scipy.spatial.transform import Rotation
import opengate_core
from .generic import GenericSource, SourceBase
from ..contrib.tps.ionbeamtherapy import (
    get_spots_from_beamset_beam,
    spots_info_from_txt,
    BeamsetInfo,
)
from ..exception import fatal, warning


class IonPencilBeamSource(GenericSource):
    """
    Pencil Beam source
    """

    type_name = "IonPencilBeamSource"

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        user_info.position.type = "disc"
        # additional parameters: direction
        # sigma, theta, epsilon, conv (0: divergent, 1: convergent)
        user_info.direction.partPhSp_x = [0, 0, 0, 0]
        user_info.direction.partPhSp_y = [0, 0, 0, 0]

    def create_g4_source(self):
        return opengate_core.GatePencilBeamSource()

    def __init__(self, user_info):
        super().__init__(user_info)
        self.__check_phSpace_params(self.user_info.direction.partPhSp_x)
        self.__check_phSpace_params(self.user_info.direction.partPhSp_y)

    def __check_phSpace_params(self, paramV):
        sigma = paramV[0]
        theta = paramV[1]
        epsilon = paramV[2]
        conv = paramV[3]
        pi = math.pi
        if epsilon == 0:
            raise ValueError(
                "Ellipse area is 0 !!! Check epsilon parameter in IonPencilBeamSource."
            )
        if pi * sigma * theta < epsilon:
            raise ValueError(
                f"pi*sigma*theta < epsilon. Provided values: sigma = {sigma}, theta = {theta}, epsilon = {epsilon}."
            )
        if conv not in [0, 1]:
            raise ValueError("convergence parameter can be only 0 or 1.")


class TreatmentPlanPBSource(SourceBase):
    """
    Treatment Plan source Pencil Beam
    """

    type_name = "TreatmentPlanPBSource"

    @staticmethod
    def set_default_user_info(user_info):
        SourceBase.set_default_user_info(user_info)
        # initial user info
        # NOTE: the parameter number of particles is defined for 0 to 1 second simulation time
        user_info.sorted_spot_generation = False
        user_info.beam_model = None
        user_info.plan_path = None
        user_info.beam_data_dict = None
        user_info.beam_nr = 1
        user_info.gantry_rot_axis = "z"
        user_info.particle = None
        user_info.flat_generation = False
        user_info.ion = Box()
        user_info.ion.Z = 0  # Z: Atomic Number
        user_info.ion.A = 0  # A: Atomic Mass (nn + np +nlambda)
        user_info.ion.E = 0  # E: Excitation energy (i.e. for metastable)
        user_info.position = Box()
        user_info.position.translation = [0, 0, 0]
        user_info.position.rotation = Rotation.identity().as_matrix()
        # NOT to be set by the user:
        user_info.positions = []
        user_info.rotations = []
        user_info.energies = []
        user_info.energy_sigmas = []
        user_info.weights = []
        user_info.pdf = []  # probability density function
        user_info.partPhSp_xV = []
        user_info.partPhSp_yV = []

    def __init__(self, user_info):
        super().__init__(user_info)

        if not self.user_info.beam_data_dict and not self.user_info.plan_path:
            raise ValueError(
                "User must provide either a tretment plan file path or a beam data dictionary with spots and gantry angle."
            )

        # if len(self.user_info.n_primaries_vector) != len(self.user_info.run_timing_intervals):
        #     raise ValueError("Particles per run must have the same length of the number of runs")

        # set pbs param
        self._set_pbs_param_all_spots()

        # set ion param
        if not self.user_info.particle.startswith("ion"):
            return
        words = self.user_info.particle.split(" ")
        if len(words) > 1:
            self.user_info.ion.Z = words[1]
        if len(words) > 2:
            self.user_info.ion.A = words[2]
        if len(words) > 3:
            self.user_info.ion.E = words[3]

    def create_g4_source(self):
        return opengate_core.GateTreatmentPlanPBSource()

    def initialize(self, run_timing_intervals):
        # initialize
        SourceBase.initialize(self, run_timing_intervals)

    def get_generated_primaries(self):
        return self.g4_source.GetGeneratedPrimaries()

    def _set_pbs_param_all_spots(self):
        # initialize vectors every time, otherwise issues with MT
        positions = []
        rotations = []
        energies = []
        energy_sigmas = []
        weights = []
        partPhSp_xV = []
        partPhSp_yV = []
        beam_nr = self.user_info.beam_nr
        plan_path = self.user_info.plan_path
        gantry_rot_axis = self.user_info.gantry_rot_axis

        # get data from plan if provided
        if plan_path:
            if str(plan_path).endswith(".txt"):
                beam_data = spots_info_from_txt(
                    plan_path, self.user_info.particle, beam_nr
                )
                self.spots = beam_data["spots"]
                gantry_angle = beam_data["gantry_angle"]
            elif str(plan_path).endswith(".dcm"):
                beamset = BeamsetInfo(plan_path)
                gantry_angle = beamset.beam_angles[beam_nr - 1]
                self.spots = get_spots_from_beamset_beam(beamset, beam_nr)
            else:
                raise ValueError(
                    "Plan path time has to be in .txt or .gantry_rot_axisdcm format"
                )
        elif self.user_info.beam_data_dict:
            self.spots = self.user_info.beam_data_dict["spots"]
            gantry_angle = self.user_info.beam_data_dict["gantry_angle"]

        # set variables for spots, to initialize pbs sources on the cpp side
        self.rotation = Rotation.from_euler(gantry_rot_axis, gantry_angle, degrees=True)
        self.translation = self.user_info.position.translation
        beamline = self.user_info.beam_model
        self.d_nozzle_to_iso = beamline.distance_nozzle_iso
        self.d_stearMag_to_iso_x = beamline.distance_stearmag_to_isocenter_x
        self.d_stearMag_to_iso_y = beamline.distance_stearmag_to_isocenter_y

        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        cal_proportion_factor = lambda d_magnet_iso: (
            1
            if (d_magnet_iso == float("inf"))
            else (d_magnet_iso - self.d_nozzle_to_iso) / d_magnet_iso
        )
        self.proportion_factor_x = cal_proportion_factor(self.d_stearMag_to_iso_x)
        self.proportion_factor_y = cal_proportion_factor(self.d_stearMag_to_iso_y)

        # probability density function
        self.user_info.pdf = self._define_pdf(
            flat_generation=self.user_info.flat_generation
        )

        for i, spot in enumerate(self.spots):
            # set energy
            energies.append(beamline.get_energy(nominal_energy=spot.energy))
            energy_sigmas.append(beamline.get_sigma_energy(nominal_energy=spot.energy))

            # position:
            positions.append(self._get_pbs_position(spot))

            # rotation:
            rotations.append(self._get_pbs_rotation(spot))

            # add weight
            if self.user_info.flat_generation:
                weights.append(spot.beamFraction * len(self.spots))
            else:
                weights.append(1.0)

            # set optics parameters
            partPhSp_xV.append(
                [
                    beamline.get_sigma_x(spot.energy),
                    beamline.get_theta_x(spot.energy),
                    beamline.get_epsilon_x(spot.energy),
                    beamline.conv_x,
                ]
            )
            partPhSp_yV.append(
                [
                    beamline.get_sigma_y(spot.energy),
                    beamline.get_theta_y(spot.energy),
                    beamline.get_epsilon_y(spot.energy),
                    beamline.conv_y,
                ]
            )
        # set vectors to user info
        self.user_info.positions = positions
        self.user_info.rotations = rotations
        self.user_info.energies = energies
        self.user_info.energy_sigmas = energy_sigmas
        self.user_info.weights = weights
        self.user_info.partPhSp_xV = partPhSp_xV
        self.user_info.partPhSp_yV = partPhSp_yV

    def _define_pdf(self, flat_generation=False):
        if flat_generation:
            pdf = [1.0 / len(self.spots) for spot in self.spots]
        else:
            pdf = [spot.beamFraction for spot in self.spots]

        # normalize vector, to assure the probabilities sum up to 1
        pdf = pdf / np.sum(pdf)

        return list(pdf)

    def _get_pbs_position(self, spot):
        # (x,y) referr to isocenter plane.
        # Need to be corrected to referr to nozzle plane
        pos = [
            (spot.xiec) * self.proportion_factor_x,
            (spot.yiec) * self.proportion_factor_y,
            self.d_nozzle_to_iso,
        ]
        # Gantry angle = 0 -> source comes from +y and is positioned along negative side of y-axis
        # https://opengate.readthedocs.io/en/latest/source_and_particle_management.html

        position = list(
            (self.rotation * Rotation.from_euler("x", np.pi / 2)).apply(pos)
            + self.translation
        )

        return position

    def _get_pbs_rotation(self, spot):
        # by default the source points in direction z+.
        # Need to account for SM direction deviation and rotation thoward isocenter (270 deg around x)
        # then rotate of gantry angle
        rotation = [0.0, 0.0, 0.0]
        beta = np.arctan(spot.yiec / self.d_stearMag_to_iso_y)
        alpha = np.arctan(spot.xiec / self.d_stearMag_to_iso_x)
        rotation[0] = -np.pi / 2 + beta
        rotation[2] = -alpha

        # apply gantry angle
        spot_rotation = (
            self.rotation * Rotation.from_euler("xyz", rotation)
        ).as_matrix()

        return spot_rotation
