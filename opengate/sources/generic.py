import numpy as np
import opengate_core as g4
from box import Box
from scipy.spatial.transform import Rotation

from opengate.actors.biasingactors import (
    AngularAcceptanceValidator,
    generic_source_default_aa,
)

from ..base import UserInfoValidatorBase, process_cls
from ..exception import fatal, warning
from ..logger import logger
from ..utility import g4_units
from .base import SourceBase
from .utility import (
    all_beta_plus_radionuclides,
    compute_cdf_and_total_yield,
    get_spectrum,
    _setter_hook_generic_source_particle,
)


def _position_parameters():
    return Box(
        {
            "type": "point",
            "radius": 0,
            "sigma_x": 0,
            "sigma_y": 0,
            "size": [0, 0, 0],
            "translation": [0, 0, 0],
            "rotation": Rotation.identity().as_matrix(),
            "confine": None,
            "dz": None,  # (when cylinder)
        }
    )


def _direction_parameters():
    return Box(
        {
            "type": "iso",
            "theta": [0, 180 * g4_units.deg],
            "phi": [0, 360 * g4_units.deg],
            "momentum": [0, 0, 1],
            "focus_point": [0, 0, 0],
            "sigma": [0, 0],
            "angular_acceptance": generic_source_default_aa(),
            "accolinearity_flag": False,
            "accolinearity_fwhm": 0.5 * g4_units.deg,
            "histogram_theta_weights": [],
            "histogram_theta_angles": [],
            "histogram_phi_weights": [],
            "histogram_phi_angles": [],
        }
    )


def energy_parameters():
    return Box(
        {
            "type": "mono",
            "mono": 0,
            "sigma_gauss": 0,
            "is_cdf": False,
            "min_energy": None,
            "max_energy": None,
            "spectrum_type": None,
            "spectrum_weights": [],
            "spectrum_energies": [],
            "histogram_weight": [],
            "histogram_energy": [],
            "spectrum_energy_bin_edges": [],
            "spectrum_histogram_interpolation": None,
        }
    )


def visualization_parameters():
    return Box(
        {
            "count": 2000,
            "color": "yellow",
            "size": 2,
        }
    )


class PositionValidator(UserInfoValidatorBase):
    """Validates the 'position' Box."""

    __schema__ = set(_position_parameters().keys())

    def validate(self, parent_obj, attr_name: str, parent_context: str = None):
        context_name = super().validate(parent_obj, attr_name, parent_context)
        b = getattr(parent_obj, attr_name)
        valid_types = {"sphere", "point", "box", "disc", "cylinder", "surface_sphere"}
        if b.type not in valid_types:
            fatal(
                f"In {context_name}: '{b.type}' is not a valid position type. "
                f"Must be one of {valid_types}."
            )
        if b.radius < 0:
            fatal(f"In {context_name}: radius must be >= 0")
        if b.sigma_x < 0:
            fatal(f"In {context_name}: sigma_x must be >= 0")
        if b.sigma_y < 0:
            fatal(f"In {context_name}: sigma_y must be >= 0")
        if len(b.size) != 3:
            fatal(f"In {context_name}: size must be a 3-vector")
        if len(b.translation) != 3:
            fatal(f"In {context_name}: translation must be a 3-vector")
        try:
            rot_array = np.array(b.rotation)
            if rot_array.shape != (3, 3):
                raise ValueError("Shape is not (3, 3)")
        except Exception:
            fatal(
                f"In {context_name}: 'rotation' must be convertible to a 3x3 matrix/array, "
                f"but got: {b.rotation}"
            )

        # check confine
        if b.confine:
            if b.type == "point":
                warning(
                    f"In {context_name}, "
                    f"confine is used, while position.type is point ... really ?"
                )
        return context_name


class DirectionValidator(UserInfoValidatorBase):
    """Validates the 'direction' Box."""

    __schema__ = set(_direction_parameters().keys())

    def validate(self, parent_obj, attr_name: str, parent_context: str = None):
        """
        Validates the properties of a given object based on pre-defined constraints and
        rules. This process ensures that specific attributes adhere to expected formats,
        ranges, or lengths to maintain consistency and avoid errors.

        Args:
            parent_obj: The parent object containing the attribute to be validated.
            attr_name: The name of the attribute to validate as a string.
            parent_context: Optional; the context name or identifier for validation.

        Returns:
            A string containing the validation context name.

        Raises:
            Generates fatal errors and halts execution if validation constraints are not met
            for the attribute, such as improper types, incorrect vector lengths, or invalid
            range values.
        """
        context_name = super().validate(parent_obj, attr_name, parent_context)
        b = getattr(parent_obj, attr_name)
        valid_types = ["iso", "histogram", "momentum", "focused", "beam2d", "cos"]
        if b.type not in valid_types:
            fatal(
                f"In {context_name}: Cannot find the direction type '{b.type}'. "
                f"Available types are {valid_types}"
            )
        # theta must be in [0, 180]
        if len(b.theta) != 2:
            fatal(f"In {context_name}: theta must be a 2-vector")
        if b.theta[0] < 0 or b.theta[1] > 180:
            fatal(
                f"In {context_name}: Theta must be in [0, 180] degrees. "
                f"Got {b.theta[0]} and {b.theta[1]}"
            )
        # phi must be in [0, 360]
        if len(b.phi) != 2:
            fatal(f"In {context_name}: phi must be a 2-vector")
        if b.phi[0] < 0 or b.phi[1] > 360:
            fatal(
                f"In {context_name}: Phi must be in [0, 360] degrees. "
                f"Got {b.phi[0]} and {b.phi[1]}"
            )
        # check the momentum
        if len(b.momentum) != 3:
            fatal(f"In {context_name}: momentum must be a 3-vector")
        # check focus point
        if len(b.focus_point) != 3:
            fatal(f"In {context_name}: focus_point must be a 3-vector")
        # sigma
        if len(b.sigma) != 2:
            fatal(f"In {context_name}: sigma must be a 2-vector")
        # check angular acceptance
        aa = AngularAcceptanceValidator()
        aa.validate(b, "angular_acceptance", context_name)
        # check histogram theta weights
        if len(b.histogram_theta_weights) > 0 or len(b.histogram_theta_angles) > 0:
            if len(b.histogram_theta_weights) != len(b.histogram_theta_angles) - 1:
                fatal(
                    f"In {context_name}: histogram_theta_weights must have -1 elements than histogram_theta_angles"
                )
        # check histogram phi weights
        if len(b.histogram_phi_weights) > 0 or len(b.histogram_phi_angles) > 0:
            if len(b.histogram_phi_weights) != len(b.histogram_phi_angles) - 1:
                fatal(
                    f"In {context_name}: histogram_phi_weights must have -1 elements than histogram_phi_angles"
                )
        return context_name


class EnergyValidator(UserInfoValidatorBase):
    """Validates the 'energy' Box."""

    __schema__ = set(energy_parameters().keys())

    def validate(self, parent_obj, attr_name: str, parent_context: str = None):
        context_name = super().validate(parent_obj, attr_name, parent_context)
        b = getattr(parent_obj, attr_name)
        # check spectrum type
        if b.spectrum_type is not None:
            valid_spectrum_types = ["discrete", "histogram", "interpolated"]
            if b.spectrum_type not in valid_spectrum_types:
                fatal(
                    f"In {context_name}: Cannot find the energy spectrum type '{b.spectrum_type}'. "
                    f"Available types are {valid_spectrum_types}"
                )
        # check type
        valid_types = [
            "mono",
            "gauss",
            "F18_analytic",
            "O15_analytic",
            "C11_analytic",
            "histogram",
            "spectrum_discrete",
            "spectrum_histogram",
        ]
        valid_types.extend(all_beta_plus_radionuclides)
        if b.type not in valid_types:
            fatal(
                f"In {context_name}: Cannot find the energy type '{b.type}'. "
                f"Available types are {valid_types}"
            )
        # check spectrum weights
        if b.spectrum_type == "discrete":
            if len(b.spectrum_weights) != len(b.spectrum_energies):
                fatal(
                    f"In {context_name}: spectrum_weights and spectrum_energies must have the same length"
                )
        elif b.spectrum_type == "histogram":
            if len(b.spectrum_energy_bin_edges) != len(
                b.spectrum_histogram_interpolation
            ):
                fatal(
                    f"In {context_name}: spectrum_energy_bin_edges and spectrum_histogram_interpolation must have the same length"
                )
        # check sigma
        if b.sigma_gauss < 0:
            fatal(f"In {context_name}: sigma_gauss must be >= 0")
        # check interpolation
        valid_types = [None, "linear"]
        if b.spectrum_histogram_interpolation not in valid_types:
            fatal(
                f"In {context_name}: Cannot find the spectrum_histogram_interpolation type '{b.spectrum_histogram_interpolation}'. "
                f"Available types are {valid_types}"
            )
        return context_name


class VisualizationValidator(UserInfoValidatorBase):
    """Validates the 'visualization' Box."""

    __schema__ = set(visualization_parameters().keys())

    def validate_color(self, color, prefix=""):
        valid_color_str = [
            "white",
            "grey",
            "gray",
            "black",
            "brown",
            "red",
            "green",
            "blue",
            "cyan",
            "magenta",
            "yellow",
        ]

        if isinstance(color, str) and not color in valid_color_str:
            fatal(
                f"{prefix}Invalid color name '{color}'. Valid color name options are: {valid_color_str}."
            )
        if isinstance(color, list):
            if len(color) > 4 or len(color) < 3:
                fatal(
                    f"{prefix}Color list must have 3 (RGB) or 4 (RGBA) elements. Got {len(color)}."
                )
            if len(color) == 3:
                color.append(1.0)  # Add alpha value of 1.0 if only RGB is provided
                logger.debug(
                    f"{prefix}Alpha value of 1.0 is added to the color list since only RGB values are provided."
                )
            for i, c in enumerate(color):
                if not isinstance(c, (int, float, np.number)):
                    fatal(
                        f"{prefix}All elements of color list must be numbers. Element {i} is not."
                    )
                if c < 0 or c > 1:
                    fatal(
                        f"{prefix}All elements of color list must be in the range [0, 1]. Element {i} is {c}."
                    )

    def validate(self, parent_obj, attr_name: str, parent_context: str = None):
        context_name = super().validate(parent_obj, attr_name, parent_context)
        b = getattr(parent_obj, attr_name)
        if b.count <= 0:
            logger.info(
                f"For source {parent_obj.name}, visualization count is set to {b.count}. No visualization will be performed."
            )
        elif b.count > 10000:
            warning(
                f"For source {parent_obj.name}, visualization count is too high ({b.count}), using 2000 instead."
            )
            b.count = 2000
        if b.size <= 0 or b.size >= 20:
            warning(
                f"For source {parent_obj.name}, visualization size must be in the range (0, 20). Got {b.size}. Using 3 instead."
            )
            b.size = 3
        self.validate_color(b.color, f"For visualization of source {parent_obj.name}: ")
        return context_name


class GenericSource(SourceBase):
    """
    GenericSource close to the G4 SPS, but a bit simpler.
    The G4 source created by this class is GateGenericSource.
    """

    # hints for IDE
    particle: str
    ion: Box
    weight: float
    weight_sigma: float
    user_particle_life_time: float
    tac_times: list
    tac_activities: list
    direction_relative_to_attached_volume: bool
    position: Box
    direction: Box
    energy: Box
    visualization: Box

    user_info_defaults = {
        "particle": (
            "gamma",
            {
                "doc": "Name of the particle generated by the source (gamma, e+ ... or an ion such as 'ion 9 18')",
                "setter_hook": _setter_hook_generic_source_particle,
            },
        ),
        "ion": (
            Box({"Z": 0, "A": 0, "E": 0}),
            {
                "doc": "If the particle is an ion, you must set Z: Atomic Number, A: Atomic Mass (nn + np +nlambda), E: Excitation energy (i.e. for metastable)"
            },
        ),
        "weight": (
            -1,
            {"doc": "Particle initial weight (for variance reduction technique)"},
        ),
        "weight_sigma": (
            -1,
            {
                "doc": "if not negative, the weights of the particle are a Gaussian distribution with this sigma"
            },
        ),
        "user_particle_life_time": (
            -1,
            {"doc": "FIXME "},
        ),
        "tac_times": (
            None,
            {
                "doc": "TAC: Time Activity Curve, this set the vector for the times. Must be used with tac_activities."
            },
        ),
        "tac_activities": (
            None,
            {
                "doc": "TAC: Time Activity Curve, this set the vector for the activities. Must be used with tac_times."
            },
        ),
        "direction_relative_to_attached_volume": (
            False,
            {
                "doc": "Should we update the direction of the particle "
                "when the volume is moved (with dynamic parametrisation)?"
            },
        ),
        "position": (
            _position_parameters(),
            {"doc": "Define the position of the primary particles"},
        ),
        "direction": (
            _direction_parameters(),
            {"doc": "Define the direction of the primary particles"},
        ),
        "energy": (
            energy_parameters(),
            {"doc": "Define the energy of the primary particles"},
        ),
        "polarization": (
            [],
            {"doc": "Polarization of the particle (3 Stokes parameters)."},
        ),
        "visualization": (
            visualization_parameters(),
            {
                "doc": "count is the number of particles to visualize, color is the color of the visualized particles and size is their size (in mm).",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        SourceBase.__init__(self, *args, **kwargs)
        # to validate the parameters
        self._pos_validator = PositionValidator()
        self._dir_validator = DirectionValidator()
        self._ene_validator = EnergyValidator()
        self._visu_validator = VisualizationValidator()
        self.total_zero_events = 0
        self.total_skipped_events = 0
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
        return g4.GateGenericSource()

    def resolve_and_validate_config(self, run_timing_intervals):
        self.resolve_tac_activity()
        super().resolve_and_validate_config(run_timing_intervals)

        # Check the sub-parameters
        self._pos_validator.validate(self, "position")
        self._ene_validator.validate(self, "energy")
        self._dir_validator.validate(self, "direction")
        self._visu_validator.validate(self, "visualization")

        if self.particle == "back_to_back":
            # force the energy to 511 keV
            self.energy.type = "mono"
            self.energy.mono = 511 * g4_units.keV

        # histogram parameters: histogram_weight, histogram_energy"
        ene = self.energy
        if ene.type == "histogram":
            if len(ene.histogram_weight) != len(ene.histogram_energy):
                fatal(
                    f'For the source {self.name}, the parameters "energy", '
                    f'"histogram_energy" and "histogram_weight" must have the same length'
                )

        # logic for half life and user_particle_life_time
        if self.half_life > 0:
            # if the user set the half life and not the user_particle_life_time
            # we force the latter to zero
            if self.user_particle_life_time < 0:
                self.user_particle_life_time = 0

        self.check_confine(self.user_info)

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        # special case for beta plus energy spectra
        # FIXME put this elsewhere
        if self.particle == "e+":
            if self.energy.type in all_beta_plus_radionuclides:
                data = get_spectrum(self.user_info.energy.type, "e+", "radar")
                ene = data[:, 0] / 1000  # convert from KeV to MeV
                proba = data[:, 1]
                cdf, _ = compute_cdf_and_total_yield(proba, ene)
                # total = total * 1000  # (because was in MeV)
                # self.user_info.activity *= total
                self.energy.is_cdf = True
                g4_source.SetEnergyCDF(ene)
                g4_source.SetProbabilityCDF(cdf)

        self.initialize_start_end_time(run_timing_intervals)
        self.check_ui_activity(self.user_info)
        self.update_tac_activity(g4_source)
        g4_source.InitializeUserInfo(self.user_info)
        # warning for non-used ?

    def check_confine(self, ui):
        # FIXME: This should rather be a function than a method
        # FIXME: self actually holds the parameters n and activity, but the ones from ui are used here.
        if ui.position.confine:
            if ui.position.type == "point":
                warning(
                    f"In source {ui.name}, "
                    f"confine is used, while position.type is point ... really ?"
                )

    def gather_outputs(self, thread_sources):
        self.total_zero_events = sum(
            g4_src.GetTotalZeroEvents()
            for g4_src in thread_sources
            if g4_src is not None
        )
        self.total_skipped_events = sum(
            g4_src.GetTotalSkippedEvents()
            for g4_src in thread_sources
            if g4_src is not None
        )

    def resolve_tac_activity(self):
        if self.tac_times is None and self.tac_activities is None:
            return
        if len(self.tac_times) != len(self.tac_activities):
            fatal(
                f"option tac_activities must have the same size as tac_times in source '{self.name}'"
            )
        # it is important to set the starting time for this source as the tac
        # may start later than the simulation timing
        self.start_time = self.tac_times[0]
        self.activity = self.tac_activities[0]

    def update_tac_activity(self, g4_source):
        if self.tac_times is None and self.tac_activities is None:
            return
        g4_source.SetTAC(self.tac_times, self.tac_activities)

    def can_predict_number_of_events(self):
        aa = self.direction.angular_acceptance
        if aa.policy == "Rejection":
            if aa.skip_policy == "ZeroEnergy":
                return True
            return False
        return True


process_cls(GenericSource)
