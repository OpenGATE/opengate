import sys
from typing import Optional

import opengate_core as g4
from ..base import GateObject
from ..exception import fatal


class FilterBase(GateObject):
    """
    A filter to be attached to an actor.
    """

    # hints for IDE
    policy: str

    user_info_defaults = {
        "policy": (
            "accept",
            {
                "doc": "How should the item be handled?",
                "allowed_values": ["accept", "reject"],
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def initialize(self):
        self.InitializeUserInput(self.user_info)

    def __setstate__(self, state):
        self.__dict__ = state
        self.__initcpp__()


class ParticleFilter(FilterBase, g4.GateParticleFilter):

    # hints for IDE
    particle: str

    user_info_defaults = {
        "particle": (
            "",
            {
                "doc": "Name of the particle to which this filter is applied.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateParticleFilter.__init__(self)


class KineticEnergyFilter(FilterBase, g4.GateKineticEnergyFilter):

    # hints for IDE
    energy_min: float
    energy_max: float

    user_info_defaults = {
        "energy_min": (
            0,
            {
                "doc": "Lower kinetic energy bound.",
            },
        ),
        "energy_max": (
            sys.float_info.max,
            {
                "doc": "Upper kinetic energy bound.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateKineticEnergyFilter.__init__(self)  # no argument in cpp side


class TrackCreatorProcessFilter(FilterBase, g4.GateTrackCreatorProcessFilter):

    # hints for IDE
    process_name: str

    user_info_defaults = {
        "process_name": (
            "none",
            {
                "doc": "Name of the track creator process to be identified.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateTrackCreatorProcessFilter.__init__(self)  # no argument in cpp side


class ThresholdAttributeFilter(FilterBase, g4.GateThresholdAttributeFilter):

    # hints for IDE
    value_min: float
    value_max: float
    attribute: Optional[str]

    user_info_defaults = {
        "value_min": (
            0,
            {
                "doc": "Lower bound. ",
            },
        ),
        "value_max": (
            sys.float_info.max,
            {
                "doc": "Upper bound. ",
            },
        ),
        "attribute": (
            None,
            {
                "doc": "Attribute name to be considered. ",
            },
        ),
    }

    # FIXME required test dans initialize

    def __init__(self, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateThresholdAttributeFilter.__init__(self)

    def initialize(self):
        if self.attribute is None:
            fatal(
                f"The user input parameter 'attribute' is not set but required in filter '{self.name}'."
            )
        super().initialize()


class UnscatteredPrimaryFilter(FilterBase, g4.GateUnscatteredPrimaryFilter):

    def __init__(self, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateUnscatteredPrimaryFilter.__init__(self)

    def initialize(self):
        super().initialize()


filter_classes = {
    "ParticleFilter": ParticleFilter,
    "KineticEnergyFilter": KineticEnergyFilter,
    "TrackCreatorProcessFilter": TrackCreatorProcessFilter,
    "ThresholdAttributeFilter": ThresholdAttributeFilter,
    "UnscatteredPrimaryFilter": UnscatteredPrimaryFilter,
}


def get_filter_class(f):
    try:
        return filter_classes[f]
    except KeyError:
        fatal(
            f"Unknown filter '{f}'. Known filters are: {list(filter_classes.keys())}."
        )
