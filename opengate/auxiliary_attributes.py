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
        g4.GateLastProcessDefinedStepInVolumeAttribute.__init__(
            self, self.user_info
        )

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
    along the track.
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
        g4.GateLastInteractionPositionInVolumeAttribute.__init__(
            self, self.user_info
        )

    def initialize(self):
        if self.volume_name is None:
            fatal(
                f"Auxiliary attribute '{self.name}' requires a volume_name "
                "before initialization."
            )
        AuxiliaryAttributeBase.initialize(self)


auxiliary_attribute_types = {
    "InteractionCounterAttribute": InteractionCounterAttribute,
    "LastInteractionPositionInVolumeAttribute": LastInteractionPositionInVolumeAttribute,
    "LastProcessDefinedStepInVolumeAttribute": LastProcessDefinedStepInVolumeAttribute,
    "ProcessDefinedStepInVolumeAttribute": ProcessDefinedStepInVolumeAttribute,
}


process_cls(AuxiliaryAttributeBase)
process_cls(InteractionCounterAttribute)
process_cls(LastInteractionPositionInVolumeAttribute)
process_cls(LastProcessDefinedStepInVolumeAttribute)
process_cls(ProcessDefinedStepInVolumeAttribute)
