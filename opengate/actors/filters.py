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
    policy: str  # deprecated

    user_info_defaults = {
        "policy": (
            None,
            {"deprecated": "Use boolean filter"},
        ),
    }

    def __init__(self, sim, *args, **kwargs) -> None:
        self.sim = sim
        if "name" not in kwargs:
            kwargs["name"] = f"filter_{uuid.uuid4()}"
        super().__init__(*args, **kwargs)
        sim.filter_manager.add_filter(self)

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def initialize(self):
        self.InitializeUserInfo(self.user_info)

    def __setstate__(self, state):
        self.__dict__ = state
        self.__initcpp__()

    def __invert__(self):
        return BooleanFilter(self.sim, operator="not", filters=[self])

    def __bool__(self):
        fatal(
            f'Filter logic error: Chained comparisons (e.g., 10 < F < 20) or the "and" keyword '
            f"are not supported by Python operator overloading. \n"
            f"Please use: (10 < F) & (F < 20)"
        )

    def __rand__(self, other):
        if isinstance(other, (int, float)):
            fatal(
                f"Precedence Error: You are trying to use '&' between a number ({other}) and a Filter.\n"
                f"Add parentheses: (F('Attribute') < {other}) & ..."
            )
        # If other is a proxy, it's also a precedence error
        if isinstance(other, AttributeProxy):
            other._precedence_error("&")
        return super().__and__(other)

    def __and__(self, other):
        # If 'other' is an AttributeProxy, the user forgot parentheses on the RHS
        if isinstance(other, AttributeProxy):
            other._precedence_error("&")
        return BooleanFilter(self.sim, operator="and", filters=[self, other])

    def __or__(self, other):
        if isinstance(other, AttributeProxy):
            other._precedence_error("|")
        return BooleanFilter(self.sim, operator="or", filters=[self, other])


class GateFilter:
    """Entry point for the sugar syntax: F = GateFilter(sim)"""

    def __init__(self, sim):
        self.sim = sim

    def __call__(self, attribute_name):
        return AttributeProxy(self.sim, attribute_name)

    def __getattr__(self, name):
        # 1. Special case: If the user asks for the Unscattered flag
        if name == "UnscatteredPrimaryFlag":
            return UnscatteredPrimaryFilter(self.sim)

        # 2. Default: Return a proxy for generic attribute comparison
        return AttributeProxy(self.sim, name)


class AttributeProxy:
    """
    Attribute Proxy helper for 'Sugar' syntax.
    Usage: F = GateFilter(sim); f = (30 * sec < F("GlobalTime")) & (F("Time") <= 70 * sec)
    """

    def __init__(self, sim, attribute_name):
        self.sim = sim
        self.name = attribute_name

    # --- Standard Operators (F < value) ---
    def __lt__(self, other):  # F < other
        return AttributeComparisonFilter(
            self.sim, attribute=self.name, value_max=other, include_max=False
        )

    def __le__(self, other):  # F <= other
        return AttributeComparisonFilter(
            self.sim, attribute=self.name, value_max=other, include_max=True
        )

    def __gt__(self, other):  # F > other
        return AttributeComparisonFilter(
            self.sim, attribute=self.name, value_min=other, include_min=False
        )

    def __ge__(self, other):  # F >= other
        return AttributeComparisonFilter(
            self.sim, attribute=self.name, value_min=other, include_min=True
        )

    def __eq__(self, other):  # F == other
        return AttributeComparisonFilter(
            self.sim, attribute=self.name, value_min=other, value_max=other
        )

    def __ne__(self, other):  # F != other
        # This returns a 'NOT' BooleanFilter wrapping an 'EQUAL' filter
        eq_filter = AttributeComparisonFilter(
            self.sim, attribute=self.name, value_min=other, value_max=other
        )
        return ~eq_filter

    # Reflected not equal: other != F
    def __rne__(self, other):
        return self.__ne__(other)

    # --- Reflected Operators (value < F) ---
    def __rt__(self, other):  # other < F  =>  F > other
        return self.__gt__(other)

    def __rle__(self, other):  # other <= F =>  F >= other
        return self.__ge__(other)

    def __rgt__(self, other):  # other > F  =>  F < other
        return self.__lt__(other)

    def __rge__(self, other):  # other >= F =>  F <= other
        return self.__le__(other)

    def _precedence_error(self, op):
        fatal(
            f'Syntax Error in filter: Use parentheses when combining filters with "{op}". \n'
            f'Correct: (F("{self.name}") < 10) {op} (F("Other") > 5)\n'
            f'Wrong:   F("{self.name}") < 10 {op} F("Other") > 5'
        )

    def __and__(self, other):
        self._precedence_error("&")

    def __or__(self, other):
        self._precedence_error("|")

    def __rand__(self, other):
        self._precedence_error("&")

    def __ror__(self, other):
        self._precedence_error("|")

    def eq(self, value):
        return AttributeComparisonFilter(
            self.sim, attribute=self.name, value_min=value, value_max=value
        )

    def contains(self, value: str):
        """
        Usage: F("ParticleName").contains("gamma")
        """
        return AttributeComparisonFilter(
            self.sim, attribute=self.name, value_min=value, mode="contains"
        )

    def not_contains(self, value: str):
        """
        Usage: F("ParticleName").not_contains("gamma")
        """
        # Create the contains filter and wrap it in a NOT
        return ~self.contains(value)

    def __invert__(self):
        fatal(
            f'Syntax Error: Misplaced "~". You cannot invert an attribute proxy directly.\n'
            f'Correct: ~(F.{self.name} == "value")\n'
            f'Wrong:   ~F.{self.name} == "value"'
        )


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
        FilterBase.__init__(self, sim, *args, **kwargs)
        self.__initcpp__()
        # sim.add_filter(self, self.name)

    def __initcpp__(self):
        g4.GateBooleanFilter.__init__(self)


class UnscatteredPrimaryFilter(FilterBase, g4.GateUnscatteredPrimaryFilter):

    def __init__(self, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateUnscatteredPrimaryFilter.__init__(self)

    def initialize(self):
        super().initialize()

    # Allow syntax: F.UnscatteredPrimaryFlag == True
    def __eq__(self, other):
        if isinstance(other, bool):
            return self if other else ~self
        return NotImplemented

    # Allow syntax: F.UnscatteredPrimaryFlag != False
    def __ne__(self, other):
        if isinstance(other, bool):
            return ~self if other else self
        return NotImplemented


class AttributeComparisonFilter(FilterBase):
    """
    Base class for attribute comparisons (Float, Int, String).
    """

    user_info_defaults = {
        "attribute": (None, {"doc": "Attribute name to be considered."}),
        "value_min": (None, {"doc": "Lower bound or target value."}),
        "value_max": (None, {"doc": "Upper bound."}),
        "include_min": (None, {"doc": "If False, strict comparision."}),
        "include_max": (None, {"doc": "If False, strict comparision."}),
    }

    def __init__(self, sim, *args, **kwargs):
        if "name" not in kwargs:
            att = kwargs["attribute"]
            vmax = kwargs.get("value_max", "")
            vmin = kwargs.get("value_min", "")
            kwargs["name"] = f"filter_{att}_{vmin}_{vmax}{uuid.uuid4()}"
        FilterBase.__init__(self, sim, *args, **kwargs)
        self.__initcpp__()

    def __new__(cls, *args, **kwargs):
        # If the user is calling the factory, choose the correct subclass
        if cls is AttributeComparisonFilter:
            val = kwargs.get("value_min")
            if isinstance(val, str):
                cls = AttributeFilterString
            elif isinstance(val, int):
                cls = AttributeFilterInt
            else:
                # Default to Double for floats or unspecified types
                cls = AttributeFilterDouble
        # Create an instance of the chosen class
        return super().__new__(cls)

    def initialize(self):
        if self.user_info.attribute is None:
            fatal(f"The parameter 'attribute' is required for filter '{self.name}'.")
        super().initialize()


class AttributeFilterDouble(AttributeComparisonFilter, g4.GateAttributeFilterDouble):
    def __init__(self, sim, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, sim, *args, **kwargs)

    def __initcpp__(self):
        g4.GateAttributeFilterDouble.__init__(self)

    def initialize(self):
        super().initialize()


class AttributeFilterInt(AttributeComparisonFilter, g4.GateAttributeFilterInt):
    def __init__(self, sim, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, sim, *args, **kwargs)

    def __initcpp__(self):
        g4.GateAttributeFilterInt.__init__(self)

    def initialize(self):
        super().initialize()


class AttributeFilterString(AttributeComparisonFilter, g4.GateAttributeFilterString):
    user_info_defaults = {
        "mode": ("equal", {"doc": "Comparison mode: 'equal', 'contains', 'start'."}),
    }

    def __init__(self, sim, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, sim, *args, **kwargs)

    def __initcpp__(self):
        g4.GateAttributeFilterString.__init__(self)

    def initialize(self):
        super().initialize()


# Registry update
filter_classes = {
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
process_cls(BooleanFilter)
process_cls(UnscatteredPrimaryFilter)
process_cls(AttributeComparisonFilter)
process_cls(AttributeFilterDouble)
process_cls(AttributeFilterInt)
process_cls(AttributeFilterString)
