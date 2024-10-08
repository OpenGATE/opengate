from box import Box
from functools import wraps

from ..definitions import __world_name__
from ..exception import fatal, GateImplementationError
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
        if len(self.interfaces_to_user_output) > 1:
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
                f"because the actor handles more than one interface to output, "
                f"namely {list(self.interfaces_to_user_output.keys())}. "
                f"You need to access the parameter for each output individually.\n"
            )
            if len(name) > 0:
                for k in self.user_output:
                    s += f"ACTOR.user_output.{k}.{name} = ...\n"
                s += "... where ACTOR is your actor object."
            fatal(s)
        return func(self, *args)

    return _with_check


class ActorBase(GateObject):

    # hints for IDE
    attached_to: str
    filters: list
    filters_boolean_operator: str
    priority: int

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
    }

    # private list of property names for interfaces already defined
    # in any actor (assuming all actors inherit from the base class)
    # Do not redefine this in inheriting classes!
    _existing_properties_to_interfaces = {}

    def __init__(self, *args, **kwargs):
        GateObject.__init__(self, *args, **kwargs)
        # this is set by the actor engine during initialization
        self.actor_engine = None
        self.user_output = Box()
        self.interfaces_to_user_output = Box()

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def __getstate__(self):
        state_dict = super().__getstate__()
        state_dict["actor_engine"] = None
        return state_dict

    def __setstate__(self, state):
        super().__setstate__(state)
        for v in self.interfaces_to_user_output.values():
            v.belongs_to_actor = self
        self.__initcpp__()
        self.__update_interface_properties__()

    # def __finalize_init__(self):
    #     super().__finalize_init__()
    #     # The following attributes exist. They are declared here to avoid warning
    #     # fFilters is not known here because ActorBase does not inherit from a cpp counterpart.
    #     self.known_attributes.add("fFilters")
    #     # output_filename is a property
    #     self.known_attributes.add("output_filename")

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

    def get_data(self, name=None, **kwargs):
        if name is not None:
            try:
                return self.interfaces_to_user_output[name].get_data(**kwargs)
            except KeyError:
                fatal(
                    f"No output '{name}' found in {self.type_name} actor '{self.name}'."
                )
        elif len(self.interfaces_to_user_output) == 1:
            list(self.interfaces_to_user_output.values())[0].get_data(**kwargs)
        elif len(self.interfaces_to_user_output) == 0:
            fatal(
                f"The {self.type_name} actor '{self.name}' does not handle any output."
            )
        else:
            fatal(
                f"The {self.type_name} actor '{self.name}' handles multiple outputs. "
                "There are 2 ways to fix this: \n"
                "1) Provide a keyword argument name=OUTPUT_NAME. \n"
                f"   Example: my_actor.get_data(name='{list(self.interfaces_to_user_output.keys())[0]}')\n"
                "2) Call get_data() via the output.\n"
                f"   Example: my_actor.{list(self.interfaces_to_user_output.keys())[0]}.get_data(). "
            )

    # *** shortcut properties ***
    @property
    @shortcut_for_single_output_actor
    def output_filename(self):
        return list(self.interfaces_to_user_output.values())[0].output_filename

    @output_filename.setter
    def output_filename(self, filename):
        if len(self.interfaces_to_user_output) > 1:
            for k, v in self.interfaces_to_user_output.items():
                v.output_filename = insert_suffix_before_extension(
                    filename, v.item_suffix, suffix_separator="_"
                )
        else:
            list(self.interfaces_to_user_output.values())[0].output_filename = filename

    @property
    @shortcut_for_single_output_actor
    def write_to_disk(self):
        return list(self.interfaces_to_user_output.values())[0].write_to_disk

    @write_to_disk.setter
    def write_to_disk(self, write_to_disk):
        for k, v in self.interfaces_to_user_output.items():
            v.write_to_disk = write_to_disk

    def get_output_path(self, name=None, **kwargs):
        if name is not None:
            try:
                return self.interfaces_to_user_output[name].get_output_path(**kwargs)
            except KeyError:
                fatal(
                    f"No output called '{name}' found in {self.type_name} actor '{self.name}'."
                )
        elif len(self.interfaces_to_user_output) == 1:
            return list(self.interfaces_to_user_output.values())[0].get_output_path(
                **kwargs
            )
        elif len(self.interfaces_to_user_output) == 0:
            fatal(
                f"The {self.type_name} actor '{self.name}' does not handle any output."
            )
        else:
            fatal(
                f"The {self.type_name} actor '{self.name}' handles multiple outputs. "
                "There are 2 ways to fix this: \n"
                "1) Provide a keyword argument name=OUTPUT_NAME. \n"
                f"   Example: my_actor.get_output_path(name='{list(self.interfaces_to_user_output.keys())[0]}')\n"
                "2) Call get_output_path() via the output.\n"
                f"   Example: my_actor.{list(self.interfaces_to_user_output.keys())[0]}.get_output_path(). "
            )

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

    def initialize(self):
        """This base class method initializes common settings and should be called in all inheriting classes."""
        # Prepare the output entries for those items
        # where the user wants to keep the data in memory
        # self.RegisterCallBack("get_output_path_string", self.get_output_path_string)
        # self.RegisterCallBack(
        #     "get_output_path_for_item_string", self.get_output_path_for_item_string
        # )

        # FIXME: needs to be updated to new actor output API
        # if len(self.user_output) > 0 and all(
        #     [v.active is False for v in self.user_output.values()]
        # ):
        #     warning(f"The actor {self.name} has no active output. ")

        for k, v in self.user_output.items():
            v.initialize()

        # Create structs on C++ side for each actor output
        # This struct is only needed by actors that handle output written in C++.
        # But it does not hurt to populate the info in C++ regardless of the actor
        # The output path can also be (re-)set by the specific actor in
        # StartSimulation or BeginOfRunActionMasterThread, if needed

        # for k, v in self.user_output.items():
        #     if len(v.data_write_config) > 1:
        #         for h, w in v.data_write_config.items():
        #             k_h = f"{k}_{h}"
        #             self.AddActorOutputInfo(k_h)
        #             self.SetWriteToDisk(k_h, w.write_to_disk)
        #             self.SetOutputPath(k_h, v.get_output_path_as_string(item=h))
        #     else:
        #         self.AddActorOutputInfo(k)
        #         self.SetWriteToDisk(k, v.write_to_disk)
        #         self.SetOutputPath(k, v.get_output_path_as_string())

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
        self,
        actor_output_class,
        name,
        can_be_deactivated=False,
        automatically_generate_interface=True,
        **kwargs,
    ):
        """Method to be called internally (not by user) in the specific actor class implementations."""

        if (actor_output_class.__name__ == ActorOutputRoot.__name__) and any(
            [
                type(v).__name__ == ActorOutputRoot.__name__
                for v in self.user_output.values()
            ]
        ):
            raise GateImplementationError("Only one ROOT output per actor supported. ")

        # # extract the user info "active" if passed via kwargs
        # active = kwargs.pop("active", None)

        self.user_output[name] = actor_output_class(
            name=name,
            simulation=self.simulation,
            belongs_to=self,
            **kwargs,
        )

        if automatically_generate_interface is True:
            # try:
            self._add_interface_to_user_output(
                actor_output_class.get_default_interface_class(), name, name
            )
            # except GateImplementationError as e:
            #     raise GateImplementationError(f"A user interface cannot automatically be added for user output {name}. "
            #                                   f"A possibly reason is that the actor output "
            #                                   f"handles data with multiple items. "
            #                                   f"The developer needs to set automatically_generated_interface=False "
            #                                   f"and create the interface manually via _add_interface_to_user_output.")
        # # specify whether this instance of actor output can be deactivated
        # # (relevant for the setter hook of the "active" parameter)
        # self.user_output[name].__can_be_deactivated__ = bool(can_be_deactivated)
        # # Now the setter of active can be used
        # if active is not None:
        #     self.user_output[name].active = active

        return self.user_output[name]

    def _add_interface_to_user_output(
        self, interface_class, user_output_name, interface_name, **kwargs
    ):
        if interface_name not in self.interfaces_to_user_output:
            self.interfaces_to_user_output[interface_name] = interface_class(
                self, user_output_name, **kwargs
            )
        else:
            raise GateImplementationError(
                f"An actor output user interface called '{interface_name}' already exists. "
            )

        self._create_interface_property(type(interface_class).__name__, interface_name)

    def _create_interface_property(self, interface_class_name, interface_name):
        # create a property in the actor so the user can quickly access the interface
        def p(self):
            return self.interfaces_to_user_output[interface_name]

        # define a unique name by combining the actor class name and the interface name
        unique_interface_name = f"{self.type_name}_{interface_name}"
        # Check if this class already has this property and whether it is associated with an interface.
        # We need to catch the case that the actor class has an attribute/property with this name for other reasons.
        if (
            hasattr(type(self), interface_name)
            and unique_interface_name not in self._existing_properties_to_interfaces
        ):
            raise GateImplementationError(
                f"Cannot create a property '{interface_name}' "
                f"for interface class {interface_class_name} "
                f"in actor {self.name} "
                f"because a property with that name already exists, "
                f"but it is not associated with the interface. "
                f"The developer needs to change the name of the interface "
                f"(or user_output in case the interface is automatically generated). "
            )
        elif not hasattr(type(self), interface_name):
            setattr(type(self), interface_name, property(p))
            self._existing_properties_to_interfaces[unique_interface_name] = (
                interface_class_name
            )
        else:
            pass

    def __update_interface_properties__(self):
        """Special method to be called when unpickling an object
        to make sure the dynamic properties linking to the interfaces are recreated.
        """

        # create properties for all interfaces of this instance
        for k, v in self.interfaces_to_user_output.items():
            # v is an instance of an interface class,
            # so type(v) is the class, and type(v).__name__ the class name
            self._create_interface_property(type(v).__name__, k)

    def recover_user_output(self, actor):
        self.user_output = actor.user_output
        # if actor comes from a subprocess, its reference actor.simulation
        # points to the simulation instance created in the subprocess
        # Therefore, we have to reset it to the right simulation instance,
        # namely the one from the main process
        for u in self.user_output.values():
            u.simulation = self.simulation
        for v in self.interfaces_to_user_output.values():
            v.belongs_to_actor = self

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

    def get_output_path_string(self, **kwargs):
        return str(self.get_output_path(**kwargs))

    def get_output_path_for_item_string(self, output_name, which, item):
        return str(self.user_output[output_name].get_output_path(which, item))

    def StartSimulationAction(self):
        """Default virtual method for inheritance"""
        pass

    def EndSimulationAction(self):
        """Default virtual method for inheritance"""
        pass
