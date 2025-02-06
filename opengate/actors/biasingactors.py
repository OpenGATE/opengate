import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units
from ..base import process_cls


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
    }


class SplittingActorBase(GenericBiasingActorBase):
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


class ComptSplittingActor(SplittingActorBase, g4.GateOptrComptSplittingActor):
    """
    This splitting actor enables process-based splitting specifically for Compton interactions. Each time a Compton
     process occurs, its behavior is modified by generating multiple Compton scattering tracks
     (splitting factor - 1 additional tracks plus the original) associated with the initial particle.
     Compton electrons produced in the interaction are also included, in accordance with the secondary cut settings
     provided by the user.
    """

    # hints for IDE
    min_weight_of_particle: float
    russian_roulette: bool
    rotation_vector_director: bool
    vector_director: list
    max_theta: float

    user_info_defaults = {
        "min_weight_of_particle": (
            0,
            {
                "doc": "Defines a minimum weight for particles. Particles with weights below this threshold will not be split, limiting the splitting cascade of low-weight particles generated during Compton interactions.",
            },
        ),
        "russian_roulette": (
            False,
            {
                "doc": "If enabled (True), applies a Russian roulette mechanism. Particles emitted in undesired directions are discarded if a random number exceeds 1 / splitting_factor",
            },
        ),
        "vector_director": (
            [0, 0, 1],
            {
                "doc": "Specifies the particle’s direction of interest for the Russian roulette. In this direction, the Russian roulette is not applied",
            },
        ),
        "rotation_vector_director": (
            False,
            {
                "doc": "If enabled, allows the vector_director to rotate based on any rotation applied to a volume to which this actor is attached",
            },
        ),
        "max_theta": (
            90 * g4_units.deg,
            {
                "doc": "Sets the angular range (in degrees) around vector_director within which the Russian roulette mechanism is not applied.",
            },
        ),
    }

    processes = ("compt",)

    def __init__(self, *args, **kwargs):
        SplittingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateOptrComptSplittingActor.__init__(self, {"name": self.name})

    def initialize(self):
        SplittingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()


class BremSplittingActor(SplittingActorBase, g4.GateBOptrBremSplittingActor):
    """
    This splitting actor enables process-based splitting specifically for bremsstrahlung process. Each time a Brem
    process occurs, its behavior is modified by generating multiple secondary Brem scattering tracks
    (splitting factor) attached to  the initial charged particle.
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
        SplittingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateBOptrBremSplittingActor.__init__(self, {"name": self.name})

    def initialize(self):
        SplittingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()


class FreeFlightActor(GenericBiasingActorBase, g4.GateOptrFreeFlightActor):
    """
    FIXME

    Warning: as a G4VBiasingOperator, the attachTo operation MUST be done
    1) before the StartSimulationAction and 2) for each thread
    So it is set in cpp Configure and ConfigureForWorker
    that is specifically called in engines.py
    in the register_sensitive_detectors function

    Also PreUserTrackingAction is needed because StartTracking is not used in MT.

    """

    # hints for IDE FIXME
    processes: list
    # user info FIXME

    # processes = ("compt", "Rayl", "phot", "conv", "GammaGeneralProc")
    # processes = ["phot"]
    # processes = ("Rayl", "phot", "conv")
    # processes = ["compt"]
    processes = ["GammaGeneralProc"]
    # particles = "gamma"

    def __init__(self, *args, **kwargs):
        GenericBiasingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateOptrFreeFlightActor.__init__(self, {"name": self.name})
        self.AddActions(
            {
                "PreUserTrackingAction",
            }
        )

    def initialize(self):
        GenericBiasingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateOptrFreeFlightActor.StartSimulationAction(self)


class SplitComptonScatteringActor(
    SplittingActorBase, g4.GateOptrSplitComptonScatteringActor
):
    """
    FIXME
    """

    # hints for IDE FIXME
    processes: list
    # user info FIXME

    user_info_defaults = {
        "max_compton_level": (
            3,
            {
                "doc": "FIXME ",
            },
        ),
        "skip_policy": ("SkipEvents", {"doc": "FIXME "}),
        "volumes": ([], {"doc": "FIXME "}),
        "intersection_flag": (False, {"doc": "FIXME "}),
        "normal_flag": (False, {"doc": "FIXME "}),
        "normal_vector": ([0, 0, 1], {"doc": "FIXME "}),
        "normal_tolerance": (3 * g4_units.deg, {"doc": "FIXME "}),
    }

    # processes = ("compt", "Rayl", "phot", "conv", "GammaGeneralProc")
    # processes = ["compt"]  # , "Rayl", "phot", "conv", "GammaGeneralProc")
    # processes = ("Rayl", "phot", "conv")
    processes = ["GammaGeneralProc"]

    def __init__(self, *args, **kwargs):
        SplittingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateOptrSplitComptonScatteringActor.__init__(self, {"name": self.name})
        self.AddActions(
            {
                "BeginOfRunAction",
                "PreUserTrackingAction",
                "SteppingAction",
            }
        )
        print("end init cpp")

    def initialize(self):
        SplittingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateOptrSplitComptonScatteringActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateOptrSplitComptonScatteringActor.EndSimulationAction(self)
        stat = self.GetSplitStats()
        c = stat["number_of_splits"] * self.splitting_factor
        ff = stat["number_of_tracks_with_free_flight"]
        print("stat", stat)
        print(f"ratio of ff compton in AA {ff / c*100} %")


process_cls(GenericBiasingActorBase)
process_cls(SplittingActorBase)
process_cls(ComptSplittingActor)
process_cls(BremSplittingActor)
process_cls(FreeFlightActor)
process_cls(SplitComptonScatteringActor)
