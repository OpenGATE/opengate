"""
Python-side wrappers for simulation-level auxiliary attributes.

Auxiliary attributes are named runtime attributes that can be consumed from
multiple places in GATE, such as ROOT-backed actors, generic filters, and
other C++ runtime components. Their defining feature is the typed getter
interface exposed by ``GateVAuxiliaryAttribute`` on the C++ side.

Some auxiliary attributes are stateful and use Geant4 hooks plus optional
track-owned slot data stored through ``GateUserTrackInformation`` to
accumulate or propagate values along a track. Others are stateless
getter-only attributes that compute their value directly from the current
``G4Step``.

These Python classes activate and configure the corresponding C++ attributes
for a given simulation. Attribute names are user-facing and must be unique
within a simulation because they are used for lookup by filters, actors, and
optional DigiAttribute exposure.
"""

from .base import GateObject, process_cls
from .exception import fatal

import opengate_core as g4


class AuxiliaryAttributeBase(GateObject):
    """
    Base class for simulation-level auxiliary attributes.
    """

    user_info_defaults = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def __setstate__(self, state):
        super().__setstate__(state)
        self.__initcpp__()

    def initialize(self):
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()


class InteractionCounterAttribute(
    AuxiliaryAttributeBase, g4.GateInteractionCounterAttribute
):
    """
    Count how often the current track has undergone a configured process.
    """

    user_info_defaults = {
        "process_name": (
            None,
            {
                "doc": "Name of the Geant4 process to count.",
            },
        ),
        "propagate_from_parent_track": (
            False,
            {
                "doc": "If true, secondaries inherit the current count snapshot from their parent at creation time.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        AuxiliaryAttributeBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateInteractionCounterAttribute.__init__(self, self.user_info)

    def initialize(self):
        if self.process_name is None:
            fatal(
                f"Auxiliary attribute '{self.name}' requires a process_name "
                "before initialization."
            )
        AuxiliaryAttributeBase.initialize(self)


class ProcessDefinedStepInVolumeAttribute(
    AuxiliaryAttributeBase, g4.GateProcessDefinedStepInVolumeAttribute
):
    """
    Count how often the configured process defined a step in the configured
    volume for the current track. Optionally propagate the current count
    snapshot to secondaries created along the track.
    """

    user_info_defaults = {
        "process_name": (
            None,
            {
                "doc": "Name of the Geant4 process to count.",
            },
        ),
        "volume_name": (
            None,
            {
                "doc": "Name of the volume in which the process count is evaluated.",
            },
        ),
        "propagate_from_parent_track": (
            False,
            {
                "doc": "If true, secondaries inherit the current count snapshot from their parent at creation time.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        AuxiliaryAttributeBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateProcessDefinedStepInVolumeAttribute.__init__(self, self.user_info)

    def initialize(self):
        if self.process_name is None:
            fatal(
                f"Auxiliary attribute '{self.name}' requires a process_name "
                "before initialization."
            )
        if self.volume_name is None:
            fatal(
                f"Auxiliary attribute '{self.name}' requires a volume_name "
                "before initialization."
            )
        AuxiliaryAttributeBase.initialize(self)


class LastProcessDefinedStepInVolumeAttribute(
    AuxiliaryAttributeBase, g4.GateLastProcessDefinedStepInVolumeAttribute
):
    """
    Store the last non-transportation process that defined a step in the
    configured volume for the current track. Optionally propagate the current
    process snapshot to secondaries created along the track.
    """

    user_info_defaults = {
        "volume_name": (
            None,
            {
                "doc": "Name of the volume in which the last process is evaluated.",
            },
        ),
        "propagate_from_parent_track": (
            False,
            {
                "doc": "If true, secondaries inherit the current process snapshot from their parent at creation time.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        AuxiliaryAttributeBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateLastProcessDefinedStepInVolumeAttribute.__init__(self, self.user_info)

    def initialize(self):
        if self.volume_name is None:
            fatal(
                f"Auxiliary attribute '{self.name}' requires a volume_name "
                "before initialization."
            )
        AuxiliaryAttributeBase.initialize(self)


class LastInteractionPositionInVolumeAttribute(
    AuxiliaryAttributeBase, g4.GateLastInteractionPositionInVolumeAttribute
):
    """
    Store the last interaction position seen on the current track inside the
    configured volume hierarchy. The stored position is taken from the
    pre-step point of the step whose defining process is not Transportation.
    Optionally propagate the current position snapshot to secondaries created
    along the track. If no qualifying interaction has been seen yet, the
    attribute returns ``(NaN, NaN, NaN)``.
    """

    user_info_defaults = {
        "volume_name": (
            None,
            {
                "doc": "Name of the volume in which the interaction position is evaluated.",
            },
        ),
        "propagate_from_parent_track": (
            False,
            {
                "doc": "If true, secondaries inherit the current interaction position snapshot from their parent at creation time.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        AuxiliaryAttributeBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateLastInteractionPositionInVolumeAttribute.__init__(self, self.user_info)

    def initialize(self):
        if self.volume_name is None:
            fatal(
                f"Auxiliary attribute '{self.name}' requires a volume_name "
                "before initialization."
            )
        AuxiliaryAttributeBase.initialize(self)


class UnscatteredPrimaryAttribute(
    AuxiliaryAttributeBase, g4.GateUnscatteredPrimaryAttribute
):
    """
    Return 1 when the current step belongs to an unscattered primary particle,
    and 0 otherwise.
    """

    def __init__(self, *args, **kwargs):
        AuxiliaryAttributeBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateUnscatteredPrimaryAttribute.__init__(self, self.user_info)


class ParticleAncestorAttribute(
    AuxiliaryAttributeBase, g4.GateParticleAncestorAttribute
):
    """
    Return the position of the first gamma ancestor of the current particle. If already exist, propagate to secondaries.
    """

    user_info_defaults = {
        "value_to_store": (
            "VertexKineticEnergy",
            {
                "doc": "The quantity to store for the first gamma ancestor. It can be: VertexKineticEnergy or VertexPosition",
            },
        ),
        "particle_name": (
            "gamma",
            {
                "doc": "The particle to search for. The quantity will be stored for the first ancestor corresponding to this particle type.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        AuxiliaryAttributeBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateParticleAncestorAttribute.__init__(self, self.user_info)


auxiliary_attribute_types = {
    "InteractionCounterAttribute": InteractionCounterAttribute,
    "LastInteractionPositionInVolumeAttribute": LastInteractionPositionInVolumeAttribute,
    "LastProcessDefinedStepInVolumeAttribute": LastProcessDefinedStepInVolumeAttribute,
    "ProcessDefinedStepInVolumeAttribute": ProcessDefinedStepInVolumeAttribute,
    "UnscatteredPrimaryAttribute": UnscatteredPrimaryAttribute,
    "ParticleAncestorAttribute": ParticleAncestorAttribute,
}


process_cls(AuxiliaryAttributeBase)
process_cls(InteractionCounterAttribute)
process_cls(LastInteractionPositionInVolumeAttribute)
process_cls(LastProcessDefinedStepInVolumeAttribute)
process_cls(ProcessDefinedStepInVolumeAttribute)
process_cls(UnscatteredPrimaryAttribute)
process_cls(ParticleAncestorAttribute)
