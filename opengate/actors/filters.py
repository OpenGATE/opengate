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
    negate: bool
    policy: str  # deprecated

    user_info_defaults = {
        "negate": (
            False,
            {"doc": "If True, invert the result of this filter."},
        ),
        "policy": (
            None,
            {"deprecated": "Use boolean filter"},
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        if "name" not in kwargs:
            kwargs["name"] = f"filter_{uuid.uuid4()}"
        super().__init__(*args, **kwargs)

    @GateObject.simulation.setter
    def simulation(self, sim):
        if sim is None:
            self._simulation = None
        else:
            GateObject.simulation.fset(self, sim)
        if isinstance(self, BooleanFilter):
            for subfilter in self.filters:
                subfilter.simulation = sim

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def initialize(self):
        self.InitializeUserInfo(self.user_info)

    def __setstate__(self, state):
        self.__dict__ = state
        self.__initcpp__()

    def __invert__(self):
        return self._clone_negated()

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
        return BooleanFilter(
            simulation=self._shared_simulation_with(other),
            operator="and",
            filters=[self, other],
        )

    def __or__(self, other):
        if isinstance(other, AttributeProxy):
            other._precedence_error("|")
        return BooleanFilter(
            simulation=self._shared_simulation_with(other),
            operator="or",
            filters=[self, other],
        )

    def _shared_simulation_with(self, other):
        if self.simulation is not None:
            return self.simulation
        if other is not None and hasattr(other, "simulation"):
            return other.simulation
        return None

    def _clone_negated(self):
        clone = type(self)(name=f"not_{self.name}")
        clone.configure_like(self)
        clone.simulation = self.simulation
        clone.negate = not self.negate
        return clone


class GateFilter:
    """Entry point for the sugar syntax: F = GateFilter()"""

    def __call__(self, attribute_name):
        return AttributeProxy(attribute_name)

    def __getattr__(self, name):
        # 1. Special case: If the user asks for the Unscattered flag
        if name == "UnscatteredPrimaryFlag":
            return UnscatteredPrimaryFilter()

        # 2. Default: Return a proxy for generic attribute comparison
        return AttributeProxy(name)


class AttributeProxy:
    """
    Attribute Proxy helper for 'Sugar' syntax.
    Usage: F = GateFilter(); f = (30 * sec < F("GlobalTime")) & (F("Time") <= 70 * sec)
    """

    def __init__(self, attribute_name):
        self.name = attribute_name

    # --- Standard Operators (F < value) ---
    def __lt__(self, other):  # F < other
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=other,
            compare_operation="lt",
        )

    def __le__(self, other):  # F <= other
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=other,
            compare_operation="le",
        )

    def __gt__(self, other):  # F > other
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=other,
            compare_operation="gt",
        )

    def __ge__(self, other):  # F >= other
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=other,
            compare_operation="ge",
        )

    def __eq__(self, other):  # F == other
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=other,
            compare_operation="eq",
        )

    def __ne__(self, other):  # F != other
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=other,
            compare_operation="ne",
        )

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
            attribute=self.name,
            compare_value=value,
            compare_operation="eq",
        )

    def contains(self, value: str):
        """
        Usage: F("ParticleName").contains("gamma")
        """
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=value,
            compare_operation="contains",
        )

    def startswith(self, value: str):
        return AttributeComparisonFilter(
            attribute=self.name,
            compare_value=value,
            compare_operation="startswith",
        )

    def one_of(self, *args):
        if len(args) == 1 and isinstance(args[0], (list, tuple, set)):
            values = list(args[0])
        else:
            values = list(args)

        if len(values) == 0:
            fatal(f'one_of() requires at least one value for attribute "{self.name}".')

        filters = [self == value for value in values]
        if len(filters) == 1:
            return filters[0]
        return BooleanFilter(filters=filters, operator="or")

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
            {"doc": "todo", "allowed_values": ("and", "or")},
        ),
    }

    def __init__(self, *args, **kwargs):
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()
        # sim.add_filter(self, self.name)

    def __initcpp__(self):
        g4.GateBooleanFilter.__init__(self)

    def _clone_negated(self):
        clone = FilterBase._clone_negated(self)
        clone.filters = list(self.filters)
        return clone


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
        "compare_value": (None, {"doc": "Reference value used by the comparison."}),
        "compare_operation": (
            None,
            {"doc": "Comparison operator shorthand such as lt, le, gt, ge, eq."},
        ),
    }

    def __init__(self, *args, **kwargs):
        if "name" not in kwargs:
            att = kwargs["attribute"]
            op = kwargs.get("compare_operation", "")
            value = kwargs.get("compare_value", "")
            kwargs["name"] = f"filter_{att}_{op}_{value}{uuid.uuid4()}"
        FilterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __new__(cls, *args, **kwargs):
        # If the user is calling the factory, choose the correct subclass
        if cls is AttributeComparisonFilter:
            val = kwargs.get("compare_value")
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
    def __init__(self, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, *args, **kwargs)

    def __initcpp__(self):
        g4.GateAttributeFilterDouble.__init__(self)

    def initialize(self):
        super().initialize()


class AttributeFilterInt(AttributeComparisonFilter, g4.GateAttributeFilterInt):
    def __init__(self, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, *args, **kwargs)

    def __initcpp__(self):
        g4.GateAttributeFilterInt.__init__(self)

    def initialize(self):
        super().initialize()


class AttributeFilterString(AttributeComparisonFilter, g4.GateAttributeFilterString):
    def __init__(self, *args, **kwargs):
        AttributeComparisonFilter.__init__(self, *args, **kwargs)

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


def bind_filter_to_simulation(filter_obj, simulation):
    if filter_obj is None:
        return None
    if not isinstance(filter_obj, FilterBase):
        fatal(
            f"Expected a FilterBase object, got {type(filter_obj).__name__}: {filter_obj}"
        )
    filter_obj.simulation = simulation
    if simulation is not None:
        _register_filter_tree(filter_obj, simulation)
    return filter_obj


def _register_filter_tree(filter_obj, simulation):
    simulation.filter_manager.add_filter(filter_obj)
    if isinstance(filter_obj, BooleanFilter):
        for subfilter in filter_obj.filters:
            _register_filter_tree(subfilter, simulation)


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
