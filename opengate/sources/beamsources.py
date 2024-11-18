import math
from box import Box
import numpy as np
from scipy.spatial.transform import Rotation
import opengate_core as g4
from .generic import GenericSource, SourceBase
from ..contrib.tps.ionbeamtherapy import (
    get_spots_from_beamset_beam,
    spots_info_from_txt,
    BeamsetInfo,
)
from ..base import process_cls


def _check_ph_space_params(param_v):
    sigma = param_v[0]
    theta = param_v[1]
    epsilon = param_v[2]
    conv = param_v[3]
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


class IonPencilBeamSource(GenericSource, g4.GatePencilBeamSource):
    """
    Pencil Beam source
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__initcpp__()
        self.position.type = "disc"

        # FIXME: how to change the user_info for this new param ? -> use "override:True" entry in options dict

        # additional parameters: direction
        # sigma, theta, epsilon, conv (0: divergent, 1: convergent)
        self.direction.partPhSp_x = [0, 0, 0, 0]
        self.direction.partPhSp_y = [0, 0, 0, 0]

    def __initcpp__(self):
        g4.GatePencilBeamSource.__init__(self)

    def initialize(self, run_timing_intervals):
        GenericSource.initialize(self, run_timing_intervals)
        _check_ph_space_params(self.direction.partPhSp_x)
        _check_ph_space_params(self.direction.partPhSp_y)


class TreatmentPlanPBSource(SourceBase, g4.GateTreatmentPlanPBSource):
    """
    Treatment Plan source Pencil Beam
    """

    user_info_defaults = {
        "sorted_spot_generation": (False, {"doc": "FIXME"}),
        "beam_model": (None, {"doc": "FIXME"}),
        "plan_path": (None, {"doc": "FIXME"}),
        "beam_data_dict": (None, {"doc": "FIXME"}),
        "beam_nr": (1, {"doc": "FIXME"}),
        "gantry_rot_axis": ("z", {"doc": "FIXME"}),
        "flat_generation": (False, {"doc": "FIXME"}),
        "particle": (None, {"doc": "FIXME"}),
        "ion": (Box({"Z": 0, "A": 0, "E": 0}), {"doc": "FIXME"}),
        "position": (
            Box(
                {"translation": [0, 0, 0], "rotation": Rotation.identity().as_matrix()}
            ),
            {"doc": "FIXME"},
        ),
        "positions": ([], {"doc": "FIXME"}),
        "rotations": ([], {"doc": "FIXME"}),
        "energies": ([], {"doc": "FIXME"}),
        "energy_sigmas": ([], {"doc": "FIXME"}),
        "weights": ([], {"doc": "FIXME"}),
        "pdf": ([], {"doc": "FIXME"}),
        "partPhSp_xV": ([], {"doc": "FIXME"}),
        "partPhSp_yV": ([], {"doc": "FIXME"}),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__initcpp__()
        # initialize internal members
        self.spots = None
        self.rotation = None
        self.translation = None
        self.d_nozzle_to_iso = None
        self.d_stear_mag_to_iso_x = None
        self.d_stear_mag_to_iso_y = None
        self.proportion_factor_x = None
        self.proportion_factor_y = None

    def __initcpp__(self):
        g4.GateTreatmentPlanPBSource.__init__(self)

    def initialize(self, run_timing_intervals):
        if not self.beam_data_dict and not self.plan_path:
            raise ValueError(
                "User must provide either a treatment plan file path or a beam data dictionary "
                "with spots and gantry angle."
            )

        # if len(self.user_info.n_primaries_vector) != len(self.user_info.run_timing_intervals):
        #     raise ValueError("Particles per run must have the same length of the number of runs")

        # set pbs param
        self._set_pbs_param_all_spots()

        # set ion param
        if self.particle.startswith("ion"):
            words = self.particle.split(" ")
            if len(words) > 1:
                self.ion.Z = words[1]
            if len(words) > 2:
                self.ion.A = words[2]
            if len(words) > 3:
                self.ion.E = words[3]

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
        beam_nr = self.beam_nr
        plan_path = self.plan_path
        gantry_rot_axis = self.gantry_rot_axis
        gantry_angle = None

        # get data from plan if provided
        if plan_path:
            if str(plan_path).endswith(".txt"):
                beam_data = spots_info_from_txt(
                    plan_path, self.particle, beam_nr
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
        elif self.beam_data_dict:
            self.spots = self.beam_data_dict["spots"]
            gantry_angle = self.beam_data_dict["gantry_angle"]

        # set variables for spots, to initialize pbs sources on the cpp side
        self.rotation = Rotation.from_euler(gantry_rot_axis, gantry_angle, degrees=True)
        self.translation = self.position.translation
        beamline = self.beam_model
        self.d_nozzle_to_iso = beamline.distance_nozzle_iso
        self.d_stear_mag_to_iso_x = beamline.distance_stearmag_to_isocenter_x
        self.d_stear_mag_to_iso_y = beamline.distance_stearmag_to_isocenter_y

        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        cal_proportion_factor = lambda d_magnet_iso: (
            1
            if (d_magnet_iso == float("inf"))
            else (d_magnet_iso - self.d_nozzle_to_iso) / d_magnet_iso
        )
        self.proportion_factor_x = cal_proportion_factor(self.d_stear_mag_to_iso_x)
        self.proportion_factor_y = cal_proportion_factor(self.d_stear_mag_to_iso_y)

        # probability density function
        self.pdf = self._define_pdf(flat_generation=self.flat_generation)

        for i, spot in enumerate(self.spots):
            # set energy
            energies.append(beamline.get_energy(nominal_energy=spot.energy))
            energy_sigmas.append(beamline.get_sigma_energy(nominal_energy=spot.energy))

            # position:
            positions.append(self._get_pbs_position(spot))

            # rotation:
            rotations.append(self._get_pbs_rotation(spot))

            # add weight
            if self.flat_generation:
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
        self.positions = positions
        self.rotations = rotations
        self.energies = energies
        self.energy_sigmas = energy_sigmas
        self.weights = weights
        self.partPhSp_xV = partPhSp_xV
        self.partPhSp_yV = partPhSp_yV

    def _define_pdf(self, flat_generation=False):
        if flat_generation:
            pdf = [1.0 / len(self.spots) for spot in self.spots]
        else:
            pdf = [spot.beamFraction for spot in self.spots]

        # normalize vector, to assure the probabilities sum up to 1
        pdf = pdf / np.sum(pdf)

        return list(pdf)

    def _get_pbs_position(self, spot):
        # (x,y) refer to isocenter plane.
        # Need to be corrected to refer to nozzle plane
        pos = [
            spot.xiec * self.proportion_factor_x,
            spot.yiec * self.proportion_factor_y,
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
        # Need to account for SM direction deviation and rotation toward isocenter (270 deg around x)
        # then rotate of gantry angle
        rotation = [0.0, 0.0, 0.0]
        beta = np.arctan(spot.yiec / self.d_stear_mag_to_iso_y)
        alpha = np.arctan(spot.xiec / self.d_stear_mag_to_iso_x)
        rotation[0] = -np.pi / 2 + beta
        rotation[2] = -alpha

        # apply gantry angle
        spot_rotation = (
            self.rotation * Rotation.from_euler("xyz", rotation)
        ).as_matrix()

        return spot_rotation


process_cls(IonPencilBeamSource)
process_cls(TreatmentPlanPBSource)
