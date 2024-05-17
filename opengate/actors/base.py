from box import Box
from functools import wraps

from ..definitions import __world_name__
from ..exception import fatal
from ..base import GateObject


def _setter_hook_attached_to(self, attached_to):
    """Hook to be attached to property setter of user input 'attached_to' in all actors.
    Allows the user input 'attached_to_volume' to be volume object or a volume name.
    """

    if isinstance(attached_to, str):
        return attached_to
    else:
        try:
            return attached_to.name
        except AttributeError:
            if isinstance(
                attached_to,
                (
                    list,
                    tuple,
                ),
            ):
                attached_to_names = []
                for a in attached_to:
                    try:
                        attached_to_names.append(a.name)
                    except AttributeError:
                        attached_to_names.append(a)
                return attached_to_names

    # something went wrong if we reached this point
    fatal(
        f"attached_to must be a volume, a volume name, "
        f"or a list/tuple of volumes or volume names. "
        f"Received: {attached_to}"
    )


def shortcut_for_single_output_actor(func):
    """Decorator for shortcut methods and properties that may be used only
    with actors that handle a single user output."""

    @wraps(func)
    def _with_check(self, *args):
        if len(self.user_output) > 1:
            try:
                # func could be a method,
                name = func.__name__
            except AttributeError:
                try:
                    # or a property
                    name = func.fget.__name__
                except AttributeError:
                    name = ""
            s = (
                f"The shortcut {name} is not available for actor {self.type_name} "
                f"because the actor handles more than one output, namely {list(self.user_output.keys())}. "
                f"You need to set the parameter for each output individually.\n"
            )
            if len(name) > 0:
                for k in self.user_output:
                    s += f"ACTOR.user_output.{k}.{name} = ...\n"
                s += "... where ACTOR is your actor object."
            fatal(s)
        return func(self, *args)

    return _with_check


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
        "extra_suffix": (
            None,
            {
                "doc": "Extra suffix to be appended to filename of all user outputs of this actor. "
                "You can also set 'extra_suffix' for specific outputs individually. ",
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

    def __getstate__(self):
        state_dict = super().__getstate__()
        state_dict["actor_engine"] = None
        return state_dict

    def __setstate__(self, state):
        self.__dict__ = state
        self.__initcpp__()

    # def _get_error_msg_output_filename(self):
    #     s = (
    #         f"The shortcut attribute output_filename is not available for this actor "
    #         f"because it handles more than one output. You need to set the output_filename "
    #         f"parameter for each output individually: \n"
    #     )
    #     for k in self.user_output:
    #         s += f"ACTOR.user_output.{k}.output_filename = ...\n"
    #     s += "... where ACTOR is your actor object."
    #     return s

    # *** shortcut properties ***
    @property
    @shortcut_for_single_output_actor
    def output_filename(self):
        # if len(self.user_output) > 1:
        #     fatal(self._get_error_msg_output_filename())
        # else:
        return list(self.user_output.values())[0].output_filename

    @output_filename.setter
    def output_filename(self, filename):
        # if len(self.user_output) > 1:
        #     fatal(self._get_error_msg_output_filename())
        # else:
        list(self.user_output.values())[0].output_filename = filename

    @property
    @shortcut_for_single_output_actor
    def writable_data_items(self):
        return list(self.user_output.values())[0].writable_data_items

    @writable_data_items.setter
    def writable_data_items(self, value):
        list(self.user_output.values())[0].writable_data_items = value

    def get_output_path(self, output_name=None, which="merged", **kwargs):
        if output_name is None:
            # if no output_name, we check if there is only one single output
            if len(self.user_output) != 1:
                fatal(
                    f"Cannot use get_output_path without setting which output_name. "
                    f"Current output_name are: {self.user_output}"
                )
            # get the first (and only) item from user_output
            output_name = list(self.user_output.keys())[0]
        if output_name not in self.user_output:
            fatal(
                f"This actor does not have any output named '{output_name}'."
                f"Available outputs are: {list(self.user_output.keys())}"
            )
        return self.user_output[output_name].get_output_path(which, **kwargs)

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
            # apply extra suffix defined at actor level to all user output items
            # unless they have their own specific extra suffix set
            if self.extra_suffix is not None and v.extra_suffix is None:
                v.extra_suffix = self.extra_suffix
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
        return self.user_output[name]

    def store_output_data(self, output_name, run_index, *data):
        self._assert_output_exists(output_name)
        self.user_output[output_name].store_data(run_index, *data)

    def write_output_to_disk_if_requested(self, output_name):
        self._assert_output_exists(output_name)
        self.user_output[output_name].write_data_if_requested()

    def _assert_output_exists(self, output_name):
        if output_name not in self.user_output:
            fatal(f"No output named '{output_name}' found for actor {self.name}.")

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
