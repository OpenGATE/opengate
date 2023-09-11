import opengate_core as g4
import opengate as gate
from .FilterBase import FilterBase


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
            gate.fatal(
                f'TrackCreatorProcessFilter "{user_info.name}" policy must be either "keep" '
                f'or "discard", while it is "{user_info.policy}"'
            )
