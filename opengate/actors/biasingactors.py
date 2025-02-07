import opengate_core as g4
from .base import ActorBase
from ..base import process_cls
from box import Box
from ..utility import g4_units


def generic_source_default_aa():
    # aa = Angular Acceptance
    # this is used to control the direction of events in
    # the generic source, but is also used in the SplitComptonActor
    deg = g4_units.deg
    return Box(
        {
            "skip_policy": "SkipEvents",
            "volumes": [],
            "intersection_flag": False,
            "normal_flag": False,
            "normal_vector": [0, 0, 1],
            "normal_tolerance": 3 * deg,
        }
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
    This splitting actor enables process-based splitting specifically for bremsstrahlung process. Each time a Brem
    process occurs, its behavior is modified by generating multiple secondary Brem scattering tracks
    (splitting factor) attached to  the initial charged particle.

    This actor is not really needed as Geant4 already propose this with:
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

    # this biased actor works only for GammaGeneralProc
    processes = ["GammaGeneralProc"]

    def __init__(self, *args, **kwargs):
        GenericBiasingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateGammaFreeFlightOptrActor.__init__(self, {"name": self.name})
        # we need to ensure that the GeneralProcess is used. The 2 next
        # lines don't work, so we used G4 macro.
        # g4_em_parameters = g4.G4EmParameters.Instance()
        # g4_em_parameters.SetGeneralProcessActive(False)
        s = f"/process/em/UseGeneralProcess true"
        self.simulation.g4_commands_before_init.append(s)

    def initialize(self):
        GenericBiasingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateGammaFreeFlightOptrActor.StartSimulationAction(self)


class ComptonSplittingFreeFlightActor(
    SplitProcessActorBase, g4.GateComptonSplittingFreeFlightOptrActor
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
        "acceptance_angle": (
            generic_source_default_aa(),
            {
                "doc": "FIXME ",
            },
        ),
        # "skip_policy": ("SkipEvents", {"doc": "FIXME "}),
        # "volumes": ([], {"doc": "FIXME "}),
        # "intersection_flag": (False, {"doc": "FIXME "}),
        # "normal_flag": (False, {"doc": "FIXME "}),
        # "normal_vector": ([0, 0, 1], {"doc": "FIXME "}),
        # "normal_tolerance": (3 * g4_units.deg, {"doc": "FIXME "}),
    }

    # processes = ("compt", "Rayl", "phot", "conv", "GammaGeneralProc")
    # processes = ["compt"]  # , "Rayl", "phot", "conv", "GammaGeneralProc")
    # processes = ("Rayl", "phot", "conv")
    processes = ["GammaGeneralProc"]

    def __init__(self, *args, **kwargs):
        SplitProcessActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateComptonSplittingFreeFlightOptrActor.__init__(self, {"name": self.name})
        self.AddActions(
            {
                "BeginOfRunAction",
                "PreUserTrackingAction",
                "SteppingAction",
            }
        )
        # we need to ensure that the GeneralProcess is used. The 2 next
        # lines don't work, we used G4 macro.
        # g4_em_parameters = g4.G4EmParameters.Instance()
        # g4_em_parameters.SetGeneralProcessActive(False)
        s = f"/process/em/UseGeneralProcess true"
        self.simulation.g4_commands_before_init.append(s)

    def initialize(self):
        SplitProcessActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateComptonSplittingFreeFlightOptrActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateComptonSplittingFreeFlightOptrActor.EndSimulationAction(self)
        stat = self.GetSplitStats()
        c = stat["nb_splits"] * self.splitting_factor
        ff = stat["nb_tracks_with_free_flight"]
        print("stat", stat)
        print(f"ratio of ff compton in AA {ff / c*100} %")


process_cls(GenericBiasingActorBase)
process_cls(SplitProcessActorBase)
process_cls(BremsstrahlungSplittingActor)
process_cls(GammaFreeFlightActor)
process_cls(ComptonSplittingFreeFlightActor)
