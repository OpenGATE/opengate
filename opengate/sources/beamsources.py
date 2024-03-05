import math
from box import Box
import numpy as np
from scipy.spatial.transform import Rotation
import opengate_core
from ..utility import g4_units
from .generic import GenericSource, SourceBase
from ..contrib.ionbeamtherapy import (
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


class TreatmentPlanSourcePB(SourceBase):
    """
    Treatment Plan source Pencil Beam
    """

    type_name = "TreatmentPlanSourcePB"

    @staticmethod
    def set_default_user_info(user_info):
        SourceBase.set_default_user_info(user_info)
        # initial user info
        user_info.n = 0
        user_info.sorted_spot_generation = True
        user_info.beam_model = None
        user_info.plan_path = None
        user_info.beam_nr = 1
        user_info.particle = None
        user_info.ion = Box()
        user_info.flat_generation = False
        user_info.n_particles_as_activity = False
        user_info.position.translation = [0, 0, 0]
        user_info.position.rotation = Rotation.identity().as_matrix()
        # NOT to be set by the user:
        user_info.positions = []
        user_info.rotations = []
        user_info.energies = []
        user_info.energy_sigmas = []
        user_info.weights = []
        user_info.activities = []
        user_info.n_particles = []
        user_info.partPhSp_xV = []
        user_info.partPhSp_yV = []

    def __init__(self, user_info):
        super().__init__(user_info)
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
        return opengate_core.GateTreatmentPlanSource()

    def initialize(self, run_timing_intervals):
        # Check user_info type
        if self.user_info.float_value is None:
            fatal(
                f"Error for source {self.user_info.name}, float_value must be a float"
            )
        if self.user_info.vector_value is None:
            fatal(
                f"Error for source {self.user_info.name}, vector_value must be a vector"
            )

        # initialize
        SourceBase.initialize(self, run_timing_intervals)

    def _set_pbs_param_all_spots(self):
        beam_nr = self.user_info.beam_nr
        plan_path = self.user_info.plan_path
        # get data from plan
        if plan_path.endswith(".txt"):
            beam_data = spots_info_from_txt(plan_path, self.user_info.particle, beam_nr)
            spots = beam_data["spots"]
            gantry_angle = beam_data["gantry_angle"]
        elif plan_path.endswith(".dcm"):
            beamset = BeamsetInfo(plan_path)
            gantry_angle = beamset.beam_angles[beam_nr - 1]
            spots = get_spots_from_beamset_beam(beamset, beam_nr)
        else:
            raise ValueError("Plan path time has to be in .txt or .dcm format")

        # set variables for spots, to initialize pbs sources on the cpp side
        self.rotation = Rotation.from_euler("z", gantry_angle, degrees=True)
        self.translation = self.user_info.position.translation
        beamline = self.user_info.beamline_model
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

        n_part_spots_V = self._sample_n_particles_spots(
            flat_generation=self.user_info.flat_generation
        )

        for i, spot in enumerate(spots):
            nspot = n_part_spots_V[i]
            if nspot == 0:
                continue

            # set energy
            # source.energy.type = "gauss"
            self.user_info.energies.append(
                beamline.get_energy(nominal_energy=spot.energy)
            )
            self.user_info.energy_sigmas.append(
                beamline.get_sigma_energy(nominal_energy=spot.energy)
            )

            # source.particle = spot.particle_name
            # source.position.type = "disc"  # pos = Beam, shape = circle + sigma

            # # set mother
            # if self.mother is not None:
            #     source.mother = self.mother

            # POSITION:
            self.user_info.positions.append(self._get_pbs_position(spot))

            # ROTATION:
            self.user_info.rotations.append(self._get_pbs_rotation(spot))

            # add weight
            if self.user_info.flat_generation:
                self.user_info.weights.append(spot.beamFraction * len(spots))

            # set number of particles
            if self.user_info.n_particles_as_activity:
                Bq = g4_units.Bq
                self.user_info.activities.append(nspot * Bq)
            else:
                # nspot = np.round(nspot)
                self.user_info.n_particles.append(nspot)

            # set optics parameters
            self.user_info.partPhSp_xV.append(
                [
                    beamline.get_sigma_x(spot.energy),
                    beamline.get_theta_x(spot.energy),
                    beamline.get_epsilon_x(spot.energy),
                    beamline.conv_x,
                ]
            )
            self.user_info.partPhSp_xV.append(
                [
                    beamline.get_sigma_y(spot.energy),
                    beamline.get_theta_y(spot.energy),
                    beamline.get_epsilon_y(spot.energy),
                    beamline.conv_y,
                ]
            )

    def _sample_n_particles_spots(self, flat_generation=False):
        if flat_generation:
            pdf = [1 / len(self.spots) for spot in self.spots]
        else:
            pdf = [spot.beamFraction for spot in self.spots]

        # normalize vector, to assure the probabilities sum up to 1
        pdf = pdf / np.sum(pdf)

        n_spots = len(self.spots)
        n_part_spots_V = np.zeros(n_spots)
        for i in range(int(self.user_info.n)):
            bin = np.random.choice(np.arange(0, n_spots), p=pdf)
            n_part_spots_V[bin] += 1

        return n_part_spots_V

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

        position = (self.rotation * Rotation.from_euler("x", np.pi / 2)).apply(
            pos
        ) + self.translation

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
