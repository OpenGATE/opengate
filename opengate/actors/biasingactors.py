import opengate_core as g4
from .base import ActorBase
from ..base import process_cls
from box import Box
from ..utility import g4_units
from .actoroutput import ActorOutputBase
from ..base import UserInfoValidatorBase
from ..exception import fatal, warning
import numpy as np


def generic_source_default_aa():
    """
    Defines the Angular Acceptance (AA) parameters for biasing.
    This controls which particle directions are accepted or rejected.
    Two main policies are available:
    - rejection: reject the particle if any check fails. SkipEvent or ZeroEnergy.
    - force direction: force the particle to be in a valid direction.
    """
    return Box(
        {
            # -----------------------------------------------------------------
            # --- Global Acceptance Policy ---
            # What to do when a particle's direction fails *any* enabled check.
            # - "ForceDirection": force the particle in a valid direction.
            # - "Rejection": if the direction is non-valid, reject the event with the skip_policy
            # - None or False: AA is not used
            "policy": None,
            # - "SkipEvents": rejection, discard the event and try again.
            # - "ZeroEnergy": rejection, keep the event, but set the particle's energy to 0.
            "skip_policy": "SkipEvents",
            "max_rejection": 10000,
            # -----------------------------------------------------------------
            # --- Target Volumes ---
            # The volume(s) that all checks are relative to.
            "target_volumes": [],
            # -----------------------------------------------------------------
            # -----------------------------------------------------------------
            # --- Biasing Checks (can be combined) ---
            # You can enable one or both of these. If both are enabled,
            # the direction must pass *both* checks to be accepted.
            # 1. Intersection Check
            "enable_intersection_check": False,
            # 2. Angle Check
            "enable_angle_check": False,
            # -----------------------------------------------------------------
            # --- Parameters for Angle Check ---
            # The "ideal" vector to compare the particle's direction against.
            "angle_check_reference_vector": [0, 0, 1],
            # --- Proximity-Based Tolerance Logic ---
            # The cutoff distance: when the particle is closer than this, the max angle is given
            # by 'angle_tolerance_proximal' and not by 'angle_tolerance_max'
            # (only with policies 'SkipEvents' or 'ZeroEnergy'
            "angle_check_proximity_distance": 0 * g4_units.cm,
            # The tolerance to use *within* the proximity_distance
            # (e.g., any direction "generally towards" the volume is fine).
            "angle_tolerance_proximal": 90 * g4_units.deg,
            # The strict tolerance to use *outside* the proximity_distance.
            "angle_tolerance_min": 0 * g4_units.deg,
            "angle_tolerance_max": 6 * g4_units.deg,
        }
    )


class AngularAcceptanceValidator(UserInfoValidatorBase):
    """Validates the 'angular_acceptance' Box."""

    __schema__ = set(generic_source_default_aa().keys())

    def validate(self, parent_obj, attr_name: str, parent_context: str = None):
        context_name = super().validate(parent_obj, attr_name, parent_context)
        b = getattr(parent_obj, attr_name)
        if b.policy is False:
            b.policy = None
        # check policy
        valid_policies = [None, "ForceDirection", "Rejection"]
        if b.policy not in valid_policies:
            fatal(
                f"In {context_name}: '{b.policy}' is not a valid policy. Must be one of {valid_policies}."
            )
        # check policy
        valid_skip_policies = ["SkipEvents", "ZeroEnergy"]
        if b.skip_policy not in valid_skip_policies:
            fatal(
                f"In {context_name}: '{b.skip_policy}' is not a valid policy. Must be one of {valid_skip_policies}."
            )
        # check normal vector
        if b.enable_angle_check:
            if len(b.angle_check_reference_vector) != 3:
                fatal(f"In {context_name}: 'normal_vector' must be a 3-vector.")
            if np.linalg.norm(b.angle_check_reference_vector) != 1:
                fatal(f"In {context_name}: 'normal_vector' must be a unit vector.")
        # if FD, angle_check is ignored
        if b.policy == "ForceDirection":
            if not b.enable_angle_check:
                fatal(
                    f"In {context_name}: 'enable_angle_check' must be True when policy is 'ForceDirection'."
                )
        if b.policy == "Rejection":
            if not b.enable_intersection_check and not b.enable_angle_check:
                fatal(
                    f"In {context_name}: at least one of 'enable_intersection_check' or 'enable_angle_check' "
                    f"must be True when policy is {b.policy}."
                )


def _setter_hook_particles(self, value):
    if isinstance(value, str):
        return [value]
    else:
        return list(value)


class GenericBiasingActorBase(ActorBase):
    """
    Actors based on the G4GenericBiasing class of GEANT4. This class provides tools to interact with GEANT4 processes
    during a simulation, allowing direct modification of process properties.
    """

    # hints for IDE
    bias_primary_only: bool
    bias_only_once: bool
    particles: list
    exclude_volumes: list
    weight_cutoff: float
    energy_cutoff: float

    user_info_defaults = {
        "bias_primary_only": (
            True,
            {
                "doc": "If true, the biasing mechanism is applied only to particles with a ParentID of 1",
            },
        ),
        "bias_only_once": (
            True,
            {
                "doc": "If true, the biasing mechanism is applied only once per particle history",
            },
        ),
        "particles": (
            [
                "all",
            ],
            {
                "doc": "Specifies the particles to split. The default value, all, includes all particles",
                "setter_hook": _setter_hook_particles,
            },
        ),
        "exclude_volumes": (
            [],
            {
                "doc": "A list of volumes where this actor's biasing is disabled, allowing particles to be tracked with normal, unbiased physics. ",
            },
        ),
        "weight_cutoff": (
            -1,
            {
                "doc": "if the particle weight become lower than this value, the particle is killed. "
            },
        ),
        "energy_cutoff": (
            0,
            {
                "doc": "if the particle energy become lower than this value, the particle is killed. "
            },
        ),
    }


class SplitProcessActorBase(GenericBiasingActorBase):
    """
    This actor  enables non-physics-based particle splitting (e.g., pure geometrical splitting) to introduce biasing
    into simulations. SplittingActorBase serves as a foundational class for particle splitting operations,
    with parameters for configuring the splitting behavior based on various conditions.
    """

    # hints for IDE
    splitting_factor: int

    user_info_defaults = {
        "splitting_factor": (
            1,
            {
                "doc": "Specifies the number of particles to generate each time the splitting mechanism is applied",
            },
        ),
    }


class BremsstrahlungSplittingActor(
    SplitProcessActorBase, g4.GateBremsstrahlungSplittingOptrActor
):
    """
    This splitting actor enables process-based splitting specifically for the Bremsstrahlung process. Each time a Brem
    process occurs, its behavior is modified by generating multiple secondary Brem scattering tracks
    (splitting factor) attached to the initial charged particle.

    This actor is not really needed as Geant4 already proposes this with:
    /process/em/setSecBiasing eBrem my_region 100 50 MeV
    But we use it as a test/example.
    """

    # hints for IDE
    processes: list

    user_info_defaults = {
        "processes": (
            ["eBrem"],
            {
                "doc": "Specifies the process split by this actor. This parameter is set to eBrem, as the actor is specifically developed for this process. It is recommended not to modify this setting.",
            },
        ),
    }

    processes = ("eBrem",)

    def __init__(self, *args, **kwargs):
        SplitProcessActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateBremsstrahlungSplittingOptrActor.__init__(self, {"name": self.name})

    def initialize(self):
        SplitProcessActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()


class GammaFreeFlightActor(GenericBiasingActorBase, g4.GateGammaFreeFlightOptrActor):
    """

    Warning: as a G4VBiasingOperator, the attachTo operation MUST be done
    1) before the StartSimulationAction and 2) for each thread
    So it is set in cpp Configure and ConfigureForWorker
    that is specifically called in engines.py
    in the register_sensitive_detectors function

    Also, PreUserTrackingAction is needed because StartTracking is not used in MT.
    """

    # hints for IDE
    processes: list
    particles: list

    # This biased actor DOES NOT work for GammaGeneralProc
    processes = ["compt", "phot", "conv", "Rayl"]
    particles = ["gamma"]

    def __init__(self, *args, **kwargs):
        GenericBiasingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateGammaFreeFlightOptrActor.__init__(self, {"name": self.name})

    def initialize(self):
        GenericBiasingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateGammaFreeFlightOptrActor.StartSimulationAction(self)


class ActorOutputScatterSplittingFreeFlightActor(ActorOutputBase):
    """
    Some output statistics computed during ScatterSplittingFreeFlightActor
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.splitting_factor = kwargs.get("belongs_to").user_info.splitting_factor

        # predefine the split_info
        self.split_info = Box()
        self.split_info.nb_tracks = 0
        self.split_info.nb_tracks_with_free_flight = 0
        self.split_info.nb_compt_splits = 0
        self.split_info.nb_rayl_splits = 0
        self.split_info.nb_compt_tracks = 0
        self.split_info.nb_rayl_tracks = 0
        self.split_info.nb_killed_non_gamma_particles = 0
        self.split_info.nb_killed_gammas_compton_level = 0
        self.split_info.nb_killed_gammas_exiting = 0
        self.split_info.compton_splitting_factor = 1
        self.split_info.rayleigh_splitting_factor = 1

    def get_processed_output(
        self, infos, compton_splitting_factor, rayleigh_splitting_factor
    ):
        self.split_info.nb_tracks = infos["nb_tracks"]
        self.split_info.nb_tracks_with_free_flight = infos["nb_tracks_with_free_flight"]
        self.split_info.nb_compt_splits = infos["nb_compt_splits"]
        self.split_info.nb_rayl_splits = infos["nb_rayl_splits"]
        self.split_info.nb_compt_tracks = infos["nb_compt_tracks"]
        self.split_info.nb_rayl_tracks = infos["nb_rayl_tracks"]
        self.split_info.nb_killed_non_gamma_particles = infos[
            "nb_killed_non_gamma_particles"
        ]
        self.split_info.nb_killed_gammas_compton_level = infos[
            "nb_killed_gammas_compton_level"
        ]
        self.split_info.nb_killed_gammas_exiting = infos["nb_killed_gammas_exiting"]
        self.split_info.compton_splitting_factor = compton_splitting_factor
        self.split_info.rayleigh_splitting_factor = rayleigh_splitting_factor
        return self.split_info

    def __str__(self):
        s = ""
        for key, value in self.split_info.items():
            s += f"{key}: {value}\n"

        if (
            self.split_info.compton_splitting_factor > 0
            and self.split_info.nb_compt_splits > 0
        ):
            f = self.split_info.nb_compt_tracks / (
                self.split_info.nb_compt_splits
                * self.split_info.compton_splitting_factor
            )
            s += f"Fraction of FF compton: {f*100:.2f} %\n"

        if (
            self.split_info.rayleigh_splitting_factor > 0
            and self.split_info.nb_rayl_splits > 0
        ):
            f = self.split_info.nb_rayl_tracks / (
                self.split_info.nb_rayl_splits
                * self.split_info.rayleigh_splitting_factor
            )
            s += f"Fraction of FF rayleigh: {f*100:.2f} %\n"

        if self.split_info.nb_compt_tracks < 1 and self.split_info.nb_rayl_tracks < 1:
            f = 0
        else:
            f = self.split_info.nb_tracks_with_free_flight / (
                self.split_info.nb_compt_tracks + self.split_info.nb_rayl_tracks
            )
        s += f"Check split vs ff (should be 100): {f*100:.2f} %\n"
        return s


class ScatterSplittingFreeFlightActor(
    SplitProcessActorBase, g4.GateScatterSplittingFreeFlightOptrActor
):
    """
    Split Compton processes for gamma. The initial gamma is tracked until it goes out of the volume.
    Split gammas are tracked with free flight and Angular Acceptance
    """

    # hints for IDE
    processes: list
    particles: list
    max_compton_level: int
    compton_splitting_factor: int
    rayleigh_splitting_factor: int
    angular_acceptance: Box
    kill_interacting_in_volumes: list

    # user info
    user_info_defaults = {
        "max_compton_level": (
            10,
            {
                "doc": "Compton are split until this max level is reached (then the initial gamma is killed).",
            },
        ),
        "compton_splitting_factor": (
            -1,
            {
                "doc": "All Compton interactions will be split by this factor (if -1, set by splitting_factor).",
            },
        ),
        "rayleigh_splitting_factor": (
            -1,
            {
                "doc": "All Rayleigh interactions will be split by this factor (if -1, set by splitting_factor).",
            },
        ),
        "angular_acceptance": (
            generic_source_default_aa(),
            {
                "doc": "Scattered photon will be limited to an angular acceptance. Several methods available, see XXX",
            },
        ),
        "kill_interacting_in_volumes": (
            [],
            {
                "doc": "When a non-split particle enters one of those volumes, it is killed.",
            },
        ),
    }

    # Do NOT work with GammaGeneralProc
    processes = ["compt", "phot", "conv", "Rayl"]
    particles = ["gamma"]

    user_output_config = {
        "info": {
            "actor_output_class": ActorOutputScatterSplittingFreeFlightActor,
        },
    }

    def __init__(self, *args, **kwargs):
        SplitProcessActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()
        self._aa_validator = AngularAcceptanceValidator()

    def __initcpp__(self):
        g4.GateScatterSplittingFreeFlightOptrActor.__init__(self, {"name": self.name})

    def __str__(self):
        s = self.user_output["info"].__str__()
        return s

    def initialize(self):
        SplitProcessActorBase.initialize(self)
        # Check the sub-parameters
        self._aa_validator.validate(self, "angular_acceptance")
        if self.user_info.compton_splitting_factor == -1:
            self.user_info.compton_splitting_factor = self.user_info.splitting_factor
        if self.user_info.rayleigh_splitting_factor == -1:
            self.user_info.rayleigh_splitting_factor = self.user_info.splitting_factor
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def EndSimulationAction(self):
        g4.GateScatterSplittingFreeFlightOptrActor.EndSimulationAction(self)
        self.user_output["info"].get_processed_output(
            self.GetBiasInformation(),
            self.user_info.compton_splitting_factor,
            self.user_info.rayleigh_splitting_factor,
        )


process_cls(GenericBiasingActorBase)
process_cls(SplitProcessActorBase)
process_cls(BremsstrahlungSplittingActor)
process_cls(GammaFreeFlightActor)
process_cls(ActorOutputScatterSplittingFreeFlightActor)
process_cls(ScatterSplittingFreeFlightActor)
