import sys

import opengate_core as g4
from ..exception import fatal, warning
from ..userelement import UserElement


class FilterBase(UserElement):
    """
    Store user information about a filter
    """

    element_type = "Filter"

    @staticmethod
    def set_default_user_info(user_info):
        UserElement.set_default_user_info(user_info)
        # no user properties for all filters (maybe later)

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from FilterBase
        super().__init__(user_info)

    def __str__(self):
        s = f"str FilterBase {self.user_info.name} of type {self.user_info.type_name}"
        return s

    def close(self):
        if self.verbose_close:
            warning(
                f"Closing FilterBase {self.user_info.type_name} {self.user_info.name}"
            )

    def __getstate__(self):
        if self.verbose_getstate:
            warning(
                f"getstate FilterBase {self.user_info.type_name} {self.user_info.name}"
            )


class ParticleFilter(g4.GateParticleFilter, FilterBase):
    type_name = "ParticleFilter"

    def set_default_user_info(user_info):
        FilterBase.set_default_user_info(user_info)
        # required user info, default values
        user_info.particle = ""
        user_info.policy = "keep"  # or "discard"

    def __init__(self, user_info):
        g4.GateParticleFilter.__init__(self)  # no argument in cpp side
        FilterBase.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter
        if user_info.policy != "keep" and user_info.policy != "discard":
            fatal(
                f'ParticleFilter "{user_info.name}" policy must be either "keep" '
                f'or "discard", while it is "{user_info.policy}"'
            )


class KineticEnergyFilter(g4.GateKineticEnergyFilter, FilterBase):
    type_name = "KineticEnergyFilter"

    def set_default_user_info(user_info):
        FilterBase.set_default_user_info(user_info)
        # required user info, default values
        user_info.energy_min = 0
        user_info.energy_max = sys.float_info.max

    def __init__(self, user_info):
        g4.GateKineticEnergyFilter.__init__(self)  # no argument in cpp side
        FilterBase.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter


class TrackCreatorProcessFilter(g4.GateTrackCreatorProcessFilter, FilterBase):
    type_name = "TrackCreatorProcessFilter"

    def set_default_user_info(user_info):
        FilterBase.set_default_user_info(user_info)
        # required user info, default values
        user_info.process_name = "none"
        user_info.policy = "keep"  # or "discard"

    def __init__(self, user_info):
        g4.GateTrackCreatorProcessFilter.__init__(self)  # no argument in cpp side
        FilterBase.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter
        if user_info.policy != "keep" and user_info.policy != "discard":
            fatal(
                f'TrackCreatorProcessFilter "{user_info.name}" policy must be either "keep" '
                f'or "discard", while it is "{user_info.policy}"'
            )


class ThresholdAttributeFilter(g4.GateThresholdAttributeFilter, FilterBase):
    type_name = "ThresholdAttributeFilter"

    def set_default_user_info(user_info):
        FilterBase.set_default_user_info(user_info)
        # required user info, default values
        user_info.value_min = 0
        user_info.value_max = sys.float_info.max
        user_info.attribute = None
        user_info.policy = "keep"  # or "discard"

    def __init__(self, user_info):
        if user_info.attribute is None:
            fatal(
                f"You must set the 'attribute' in the "
                f"ThresholdAttributeFilter named {user_info._name}"
            )
        if user_info.policy != "keep" and user_info.policy != "discard":
            fatal(
                f'ThresholdAttributeFilter "{user_info.name}" policy must be either "keep" '
                f'or "discard", while it is "{user_info.policy}"'
            )
        g4.GateThresholdAttributeFilter.__init__(self)  # no argument in cpp side
        FilterBase.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter
