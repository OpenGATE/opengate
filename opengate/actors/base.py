from box import Box
from functools import wraps

from ..definitions import __world_name__
from ..exception import fatal, warning
from ..base import GateObject
from ..utility import insert_suffix_before_extension
from .actoroutput import ActorOutputRoot


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

    def to_dictionary(self):
        d = super().to_dictionary()
        d["user_output"] = dict(
            [(k, v.to_dictionary()) for k, v in self.user_output.items()]
        )
        return d

    def from_dictionary(self, d):
        super().from_dictionary(d)
        # Create all actor output objects
        for k, v in d["user_output"].items():
            self.user_output[k].from_dictionary(v)

    def get_output_data(self, output_name=None, **kwargs):
        if len(self.user_output) > 1:
            if output_name is None:
                fatal(
                    f"This actor handles multiple outputs. "
                    f"Therefore, you need to specify which. "
                    f"Example: '.get_output_data(output_name='{list(self.user_output.keys())[0]}'). "
                    f"The available output names are: {list(self.user_output.keys())}"
                )
            try:
                user_output = self.user_output[output_name]
            except KeyError:
                fatal(
                    f"No user output '{output_name}' is handled by the {self.type_name} actor '{self.name}'. "
                    f"The available output names are: {list(self.user_output.keys())}"
                )
        else:
            user_output = list(self.user_output.values())[0]
        return user_output.get_data(**kwargs)

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
    def output_filename(self):
        if len(self.user_output) > 1:
            return Box([(k, v.output_filename) for k, v in self.user_output.items()])
        else:
            return list(self.user_output.values())[0].output_filename

    @output_filename.setter
    def output_filename(self, filename):
        if len(self.user_output) > 1:
            for k, v in self.user_output.items():
                v.output_filename = insert_suffix_before_extension(
                    filename, k, suffix_separator="_"
                )
        else:
            list(self.user_output.values())[0].output_filename = filename

    @property
    def write_to_disk(self):
        if len(self.user_output) > 1:
            return Box([(k, v.write_to_disk) for k, v in self.user_output.items()])
        else:
            return list(self.user_output.values())[0].write_to_disk

    @write_to_disk.setter
    def write_to_disk(self, write_to_disk):
        for k, v in self.user_output.items():
            v.set_write_to_disk("all", write_to_disk)

    def get_output_path(self, output_name=None, which="merged", **kwargs):
        if output_name is None:
            # if no output_name, we check if there is only one single output
            if len(self.user_output) != 1:
                fatal(
                    f"This actor handles multiple outputs. "
                    f"Therefore, you need to specify which.\n"
                    f"Example: '.get_output_path(output_name='{list(self.user_output.keys())[0]}').\n"
                    f"The available output names are: {list(self.user_output.keys())}"
                )
            # get the first (and only) item from user_output
            output_name = list(self.user_output.keys())[0]
        if output_name not in self.user_output:
            fatal(
                f"This actor does not have any output named '{output_name}'."
                f"Available outputs are: {list(self.user_output.keys())}"
            )
        return self.user_output[output_name].get_output_path(which=which, **kwargs)

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
        """This base class method initializes common settings and should be called in all inheriting classes."""
        # Prepare the output entries for those items
        # where the user wants to keep the data in memory
        # self.RegisterCallBack("get_output_path_string", self.get_output_path_string)
        # self.RegisterCallBack(
        #     "get_output_path_for_item_string", self.get_output_path_for_item_string
        # )

        if len(self.user_output) > 0 and all(
            [v.active is False for v in self.user_output.values()]
        ):
            warning(f"The actor {self.name} has no active output. ")

        for k, v in self.user_output.items():
            v.initialize()

        # Create structs on C++ side for each actor output
        # This struct is only needed by actors that handle output written in C++.
        # But it does not hurt to populate the info in C++ regardless of the actor
        # The output path can also be (re-)set by the specific actor in
        # StartSimulation or BeginOfRunActionMasterThread, if needed
        for k, v in self.user_output.items():
            if len(v.data_write_config) > 1:
                for h, w in v.data_write_config.items():
                    k_h = f"{k}_{h}"
                    self.AddActorOutputInfo(k_h)
                    self.SetWriteToDisk(k_h, w.write_to_disk)
                    self.SetOutputPath(k_h, v.get_output_path_as_string(item=h))
            else:
                self.AddActorOutputInfo(k)
                self.SetWriteToDisk(k, v.write_to_disk)
                self.SetOutputPath(k, v.get_output_path_as_string())

        # initialize filters
        try:
            self.fFilters = self.filters
        except AttributeError:
            fatal(
                f"Implementation error: Unable to set the attribute 'fFilters' in actor '{self.name}' "
                f"(actor type: {self.type_name}). "
                f"Does the actor class somehow inherit from GateVActor (as it should)?"
            )

    def _add_user_output(
        self, actor_output_class, name, can_be_deactivated=False, **kwargs
    ):
        """Method to be called internally (not by user) in the specific actor class implementations."""

        if (actor_output_class.__name__ == ActorOutputRoot.__name__) and any(
            [
                type(v).__name__ == ActorOutputRoot.__name__
                for v in self.user_output.values()
            ]
        ):
            fatal("Implementation error: Only one ROOT output per actor supported. ")

        # extract the user info "active" if passed via kwargs
        try:
            active = kwargs.pop("active")
        except KeyError:
            active = None

        self.user_output[name] = actor_output_class(
            name=name,
            simulation=self.simulation,
            belongs_to=self,
            **kwargs,
        )
        # specify whether this instance of actor output can be deactivated
        # (relevant for the setter hook of the "active" parameter)
        self.user_output[name].__can_be_deactivated__ = bool(can_be_deactivated)
        # Now the setter of active can be used
        if active is not None:
            self.user_output[name].active = active

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
