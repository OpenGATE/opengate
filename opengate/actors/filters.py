import sys
import uuid
from typing import Optional
import opengate_core as g4
from ..base import GateObject, process_cls
from ..exception import fatal


class FilterBase(GateObject):
    """
    A filter to be attached to an actor.
    """

    # hints for IDE
    policy: str

    user_info_defaults = {
        "policy": (
            "accept",  # FIXME TO REMOVE !!
            {
                "doc": "How should the item be handled?",
                "allowed_values": ["accept", "reject"],
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        print("FilterBase init")
        if "name" not in kwargs:
            kwargs["name"] = f"filter_{uuid.uuid4()}"
        super().__init__(*args, **kwargs)
        # sim.add_filter(self, self.name)

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def initialize(self):
        print("FilterBase initialize")
        self.InitializeUserInfo(self.user_info)

    def __setstate__(self, state):
        print("FilterBase __setstate__ before initcpp")
        self.__dict__ = state
        self.__initcpp__()

    """def __and__(self, other):
        return BooleanFilter(operator="and", filters=[self, other])

    def __or__(self, other):
        return BooleanFilter(operator="or", filters=[self, other])

    def __invert__(self):
        return BooleanFilter(operator="not", filters=[self])"""


class BooleanFilter(FilterBase, g4.GateBooleanFilter):
    user_info_defaults = {
        "filters": (
            [],
            {"doc": "todo"},
        ),
        "operator": (
            None,
            {"doc": "todo"},
        ),
    }

    def __init__(self, sim, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()
        sim.add_filter(self, self.name)

    def __initcpp__(self):
        g4.GateBooleanFilter.__init__(self)

    def initialize(self):
        print("BooleanFilter initialize")
        """# 1. Initialize the children first so their C++ attributes are ready
        if "filters" in self.user_info:
            for f in self.user_info["filters"]:
                print('filter to init', f)
                # If it's a GateObject (Python side), call its initialize
                #if hasattr(f, "initialize"):
                    #f.initialize()

        # 2. Convert Python filter objects to C++ pointers for the user_info dict
        # This is crucial so the C++ side gets the actual GateVFilter* pointers
        #cpp_filters = [f if not hasattr(f, "g4_obj") else f.g4_obj for f in self.filters]
        #self.user_info["filters"] = cpp_filters
        print('here')"""

        # 3. Initialize the C++ side of this BooleanFilter
        super().initialize()


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


class AttributeComparisonFilter(FilterBase):
    """
    Base class for attribute comparisons (Float, Int, String).
    """

    user_info_defaults = {
        "attribute": (None, {"doc": "Attribute name to be considered."}),
        "value_min": (None, {"doc": "Lower bound or target value."}),
        "value_max": (None, {"doc": "Upper bound."}),
    }

    def __init__(self, sim, *args, **kwargs):
        print("AttributeComparisonFilter (generic) init")
        FilterBase.__init__(self, *args, **kwargs)
        print(self.user_info.value_min)
        self.__initcpp__()
        sim.add_filter(self, self.name)
        print("after add filter")

    def __new__(cls, *args, **kwargs):
        print("AttributeComparisonFilter new")
        # If the user is calling the factory, choose the correct subclass
        if cls is AttributeComparisonFilter:
            val = kwargs.get("value_min")
            if isinstance(val, str):
                print("string")
                cls = AttributeFilterString
            elif isinstance(val, int):
                print("int")
                cls = AttributeFilterInt
            else:
                # Default to Double for floats or unspecified types
                print("double")
                cls = AttributeFilterDouble

        print("here")
        # Create an instance of the chosen class
        return super().__new__(cls)

    def initialize(self):
        print("AttributeComparisonFilter initialize")
        print(self.user_info)
        if self.user_info.attribute is None:
            fatal(f"The parameter 'attribute' is required for filter '{self.name}'.")
        super().initialize()
        print("AttributeComparisonFilter initialize done", self.user_info.name)


class AttributeFilterDouble(AttributeComparisonFilter, g4.GateAttributeFilterDouble):
    def __init__(self, sim, *args, **kwargs):
        print("AttributeFilterDouble init")
        AttributeComparisonFilter.__init__(self, sim, *args, **kwargs)

    def __initcpp__(self):
        print("AttributeFilterDouble init cpp")
        g4.GateAttributeFilterDouble.__init__(self)
        print("AttributeFilterDouble init cpp done")

    def initialize(self):
        print("AttributeFilterDouble initialize", self.user_info.name)
        super().initialize()
        print("AttributeFilterDouble initialize done", self.user_info.name)


class AttributeFilterInt(AttributeComparisonFilter, g4.GateAttributeFilterInt):
    def __init__(self, sim, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, sim, *args, **kwargs)

    def __initcpp__(self):
        g4.GateAttributeFilterInt.__init__(self)

    def initialize(self):
        print("AttributeFilterInt initialize", self.user_info.name)
        super().initialize()
        print("AttributeFilterInt initialize done", self.user_info.name)


class AttributeFilterString(AttributeComparisonFilter, g4.GateAttributeFilterString):
    user_info_defaults = {
        "mode": ("equal", {"doc": "Comparison mode: 'equal', 'contains', 'start'."}),
    }

    def __init__(self, sim, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, sim, *args, **kwargs)

    def __initcpp__(self):
        g4.GateAttributeFilterString.__init__(self)

    def initialize(self):
        print("AttributeFilterString initialize", self.user_info.name)
        super().initialize()
        print("AttributeFilterString initialize done", self.user_info.name)


# Registry update
filter_classes = {
    "ParticleFilter": ParticleFilter,
    "KineticEnergyFilter": KineticEnergyFilter,
    "TrackCreatorProcessFilter": TrackCreatorProcessFilter,
    "ThresholdAttributeFilter": ThresholdAttributeFilter,
    "UnscatteredPrimaryFilter": UnscatteredPrimaryFilter,
    "AttributeFilterDouble": AttributeFilterDouble,
    "AttributeFilterInt": AttributeFilterInt,
    "AttributeFilterString": AttributeFilterString,
    "BooleanFilter": BooleanFilter,
}


def get_filter_class(f):
    try:
        return filter_classes[f]
    except KeyError:
        fatal(
            f"Unknown filter '{f}'. Known filters are: {list(filter_classes.keys())}."
        )


process_cls(FilterBase)
process_cls(ParticleFilter)
process_cls(KineticEnergyFilter)
process_cls(TrackCreatorProcessFilter)
process_cls(ThresholdAttributeFilter)
process_cls(UnscatteredPrimaryFilter)
process_cls(AttributeFilterDouble)
process_cls(AttributeFilterInt)
process_cls(AttributeFilterString)
process_cls(BooleanFilter)
