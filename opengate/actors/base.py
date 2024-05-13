from ..definitions import __world_name__
from ..exception import warning, fatal
from ..base import GateObject
from box import Box
import copy


def _setter_hook_attached_to(self, attached_to):
    """Hook to be attached to property setter of user input 'attached_to' in all actors.
    Allows the user input 'attached_to_volume' to be volume object or a volume name.
    """
    # duck typing: allow volume objects or their name
    try:
        attached_to_name = attached_to.name
    except AttributeError:
        attached_to_name = attached_to
    return attached_to_name


class ActorBase(GateObject):
    user_info_defaults = {
        "attached_to": (
            __world_name__,
            {
                "doc": "Name of the volume to which the actor is attached.",
                "setter_hook": _setter_hook_attached_to,
            },
        ),
        "mother": (
            None,
            {
                "deprecated": "The user input parameter 'mother' is deprecated. Use 'attached_to' instead. ",
            },
        ),
        "filters": (
            [],
            {
                "doc": "Filters used by this actor. ",
            },
        ),
        "filters_boolean_operator": (
            "and",
            {
                "doc": "Boolean operator to join the filters of this actor. ",
                "allowed_values": (
                    "and",
                    "or",
                ),
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
        "output_filename": (
            "auto",
            {
                "doc": "Where should the output of this actor be stored? "
                "If a filename or a relative path is provided, "
                "this is considered relative to the global simulation output folder "
                "specified in Simulation.output_path. "
                "Use an absolute path to write somewhere else on your system. "
                "If output_filename is set to 'auto', the filename is constructed automatically from "
                "the type of actor and the actor name. "
            },
        ),
        "keep_output_data": (
            False,
            {
                "doc": "Should the output data be kept as part of this actor? "
                "If `True`, you can access the data directly after the simulation. "
                "If `False`, you need to re-read the data from disk. "
            },
        ),
        "keep_data_per_run": (
            False,
            {
                "doc": "In case the simulation has multiple runs, should separate results per run be kept?"
            },
        ),
        "merge_data_from_runs": (
            True,
            {
                "doc": "In case the simulation has multiple runs, should results from separate runs be merged?"
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        GateObject.__init__(self, *args, **kwargs)

        self.actor_engine = (
            None  # this is set by the actor engine during initialization
        )
        self.user_output = Box()

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def __setstate__(self, state):
        self.__dict__ = state
        self.__initcpp__()

    @property
    def actor_type(self):
        return str(type(self).__name__)

    @property
    def actor_manager(self):
        return self.simulation.actor_manager

    @property
    def attached_to_volume(self):
        return self.simulation.volume_manager.get_volume(self.attached_to)

    def close(self):
        for uo in self.user_output.values():
            uo.close()
        for v in self.__dict__:
            if "g4_" in v:
                self.__dict__[v] = None
        self.actor_engine = None
        super().close()

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["filter_objects"] = {}
        return_dict["actor_engine"] = None
        return return_dict

    def initialize(self):
        """'Virtual' method to allow for inheritance."""
        # Prepare the output entries for those items
        # where the user wants to keep the data in memory
        # self.RegisterCallBack("get_output_path_string", self.get_output_path_string)
        # self.RegisterCallBack(
        #     "get_output_path_for_item_string", self.get_output_path_for_item_string
        # )
        for k, v in self.user_output.items():
            v.initialize()

    def _add_user_output(self, actor_output_class, name, **kwargs):
        """Method to be called internally (not by user) from the initialize_output() methods
        of the specific actor class implementations."""
        self.user_output[name] = actor_output_class(
            name=name,
            simulation=self.simulation,
            belongs_to=self,
            **kwargs,
        )

    def store_output_data(self, output_name, run_index, *data):
        self._assert_output_exists(output_name)
        self.user_output[output_name].store_data(run_index, *data)

    def write_output_to_disk_if_requested(self, output_name):
        self._assert_output_exists(output_name)
        self.user_output[output_name].write_data_if_requested()

    def _assert_output_exists(self, output_name):
        if output_name not in self.user_output:
            fatal(f"No output named '{output_name}' found for actor {self.name}.")

    def get_output_path(self, output_name, which):
        return self.user_output[output_name].get_output_path(which)

    def get_output_path_for_item(self, output_name, which, item):
        return self.user_output[output_name].get_output_path(which, item)

    def get_output_path_string(self, output_name, which):
        return str(self.get_output_path(output_name, which))

    def get_output_path_for_item_string(self, output_name, which, item):
        return str(self.user_output[output_name].get_output_path(which, item))

    def StartSimulationAction(self):
        """Default virtual method for inheritance"""
        pass

    def EndSimulationAction(self):
        """Default virtual method for inheritance"""
        pass
