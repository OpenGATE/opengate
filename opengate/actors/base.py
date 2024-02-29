from ..userelement import UserElement
from ..definitions import __world_name__
from ..exception import warning, fatal
from ..base import GateObject


def _setter_hook_user_info_mother(self, mother):
    """Hook to be attached to property setter of user info 'mother' in all actors.
    Allows the user input 'mother' to be volume object or a volume name.
    """
    # duck typing: allow volume objects or their name
    try:
        mother_name = mother.name
    except AttributeError:
        mother_name = mother
    return mother_name


def _setter_hook_filter_boolean_operator(self, value):
    allowed_values = ["and", "or"]
    if value not in allowed_values:
        fatal(
            f'The "filters_boolean_operator" option of the actor '
            f'"{self.name}" must be one of the following words: {allowed_values}. '
            f'The provided value is "value"'
        )
    return value


class ActorBase(GateObject):

    user_info_defaults = {
        "mother": (
            __world_name__,
            {
                "doc": "Name of the volume to which the actor is attached.",
                "setter_hook": _setter_hook_user_info_mother,
            },
        ),
        "filters": ([], {"doc": "List of filters used by this actor. "}),
        "filters_boolean_operator": (
            "and",
            {
                "doc": "Boolean operator to join the filters of this actor. ",
                "setter_hook": _setter_hook_filter_boolean_operator,
            },
        ),
        "priority": (
            100,
            {
                "doc": "Indicates where the actions of this actor should be placed "
                "in the list of all actions in the simulation. "
                "Low values mean 'early in the list', large values mean 'late in the list'. "
            },
        ),
    }


def __init__(self, *args, simulation=None, **kwargs):
    super().__init__(*args, **kwargs)

    self.actor_manager = None
    if simulation is not None:
        self.simulation = simulation
    self.actor_engine = None  # this is set by the actor engine during initialization

    self.filter_objects = {}  # dictionary containing the filter objects once intialized

    def close(self):
        self.actor_engine = None
        for v in self.__dict__:
            if "g4_" in v:
                self.__dict__[v] = None
        for filter in self.filter_objects.values():
            filter.close()
        self.filter_objects = {}

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["filter_objects"] = {}
        return_dict["actor_engine"] = None
        return return_dict


# class ActorBaseOld(UserElement):
#     """
#     Store user information about an actor
#     """
#
#     element_type = "Actor"
#
#     @staticmethod
#     def set_default_user_info(user_info):
#         UserElement.set_default_user_info(user_info)
#         # user properties shared for all actors
#         user_info.mother = __world_name__
#         user_info.filters = []
#         user_info.filters_boolean_operator = "and"
#         user_info.priority = 100
#
#     def __init__(self, user_info):
#         # type_name MUST be defined in class that inherit from ActorBase
#         super().__init__(user_info)
#         # list of filters for this actor
#         self.filters_list = []
#         # store the output
#         # FIXME: check if this is needed. Does not seem to be used anywhere
#         self.actor_output = None
#         # engines
#         self.simulation_engine_wr = None
#         self.volume_engine = None
#         # sim
#         self.simulation = None
#
#     def close(self):
#         if self.verbose_close:
#             warning(
#                 f"Closing ActorBase {self.user_info.type_name} {self.user_info.name}"
#             )
#         self.volume_engine = None
#         self.simulation_engine_wr = None
#         self.simulation = None
#         for v in self.__dict__:
#             if "g4_" in v:
#                 self.__dict__[v] = None
#         for filter in self.filters_list:
#             filter.close()
#
#     def __getstate__(self):
#         """
#         This is important : to get actor's outputs from a simulation run in a separate process,
#         the class must be serializable (pickle).
#         The engines (volume, actor, etc.) and G4 objects are also removed if exists.
#         """
#         if self.verbose_getstate:
#             warning(
#                 f"Getstate ActorBase {self.user_info.type_name} {self.user_info.name}"
#             )
#         # do not pickle engines and g4 objects
#         for k in self.__dict__:
#             if "_engine" in k or "g4_" in k:
#                 self.__dict__[k] = None
#         try:
#             self.__dict__["simulation"] = None
#         except KeyError:
#             print("No simulation to be removed while pickling Actor")
#         # we remove the filter that trigger a pickle error
#         # (to be modified)
#         # FIXME: the filters should implement their __getstate__ method to be pickleable
#         self.filters_list = []
#         return self.__dict__
#
#     def initialize(self, simulation_engine_wr=None):
#         self.simulation_engine_wr = simulation_engine_wr
#         self.volume_engine = self.simulation_engine_wr().volume_engine
#         if self.user_info.filters_boolean_operator not in ["and", "or"]:
#             fatal(
#                 f'The "filters_boolean_operator" option of the actor '
#                 f'"{self.user_info.name}" must be "and" or "or" while '
#                 f'it is "{self.user_info.filters_boolean_operator}"'
#             )
#
#     def __str__(self):
#         s = f"str ActorBase {self.user_info.name} of type {self.user_info.type_name}"
#         return s
