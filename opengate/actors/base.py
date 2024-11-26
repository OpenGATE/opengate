from box import Box
from functools import wraps

from ..definitions import __world_name__
from ..exception import fatal, GateImplementationError
from ..base import GateObject, process_cls
from ..utility import insert_suffix_before_extension
from .actoroutput import ActorOutputRoot, make_actor_output_class


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
                "doc": "Boolean operator to join multiple filters of this actor. ",
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

    user_output_config = {}

    # private list of property names for interfaces already defined
    # in any actor (assuming all actors inherit from the base class)
    # Do not redefine this in inheriting classes!
    _existing_properties_to_interfaces = []
    _user_output_classes = {}

    @classmethod
    def __process_user_output_classes__(cls):
        cls._user_output_classes = {}
        for output_name, output_config in cls.user_output_config.items():
            # if output_name not in cls._user_output_classes:
            try:
                actor_output_class = output_config["actor_output_class"]
            except KeyError:
                raise GateImplementationError(
                    f"In actor {cls.__name__}: "
                    f"No entry 'actor_output_class' specified "
                    f"in user_output_config for user_output {output_name}."
                )

            # default to "auto" if output_config has no key "interfaces"
            interfaces = output_config.get("interfaces", "auto")
            # no interfaces defined -> generate one automatically
            # if the GATE developer has not defined any interfaces, we create one automatically
            if interfaces == "auto":
                interface_name = output_name  # use the output name as interface name
                interfaces = {
                    interface_name: {
                        "interface_class": actor_output_class.get_default_interface_class()
                    }
                }
                # pick up parameters from the output config (where the GATE developer might have put them)
                # and add them to the interface config
                config_for_auto_interface = dict(
                    [
                        (k, v)
                        for k, v in output_config.items()
                        if k not in ("actor_output_class", "interfaces")
                    ]
                )
                config_for_auto_interface["item"] = 0
                interfaces[interface_name].update(config_for_auto_interface)
            new_class_name = f"{actor_output_class.__name__}_{output_name}_{cls.__name__}"
            cls._user_output_classes[output_name] = make_actor_output_class(
                output_name, actor_output_class, new_class_name, interfaces, cls
            )
        cls.__doc__ += cls.__get_docstring_user_output__()

    @classmethod
    def __process_this__(cls):
        """This is a specialized version of the class method __process_this__ for actor classes."""
        super().__process_this__()
        cls.__process_user_output_classes__()
        cls.__create_interface_properties__()

    @classmethod
    def __create_interface_properties__(cls):
        cls._existing_properties_to_interfaces = []
        for user_output_class in cls._user_output_classes.values():
            # create a property in the actor so the user can quickly access the interface
            for interface_name, config in user_output_class.__interfaces__.items():

                def p(self):
                    return self.interfaces_to_user_output[interface_name]

                # define a unique name by combining the actor class name and the interface name
                # unique_interface_name = f"{actor_class.__name__}_{interface_name}"
                unique_interface_name = interface_name
                # Check if this class already has this property and whether it is associated with an interface.
                # We need to catch the case that the actor class has an attribute/property with this name for other reasons.
                if (
                        hasattr(cls, interface_name)
                        and unique_interface_name
                        not in cls._existing_properties_to_interfaces
                ):
                    # before we raise an exception, we check if this property was created by a parent class
                    properties_in_bases = []
                    for c in cls.__bases__:
                        try:
                            properties_in_bases.extend(c._existing_properties_to_interfaces)
                        except AttributeError:
                            continue
                    # if the property was not created by a parent class, it must be another attribute of this class,
                    # and we should not override it.
                    if unique_interface_name not in properties_in_bases:
                        raise GateImplementationError(
                            f"Cannot create the property for interface '{interface_name}'\n"
                            f"associated with output class {user_output_class} "
                            f"in actor {cls.__name__} \n"
                            f"because a property with that name already exists, "
                            f"but it is not associated with the interface. \n"
                            f"These are the exiting properties: {cls._existing_properties_to_interfaces}\n"
                            f"The developer needs to change the name of the interface "
                            f"(or user_output in case the interface is automatically generated). "
                        )
                elif not hasattr(cls, interface_name):
                    doc_string = user_output_class.__get_docstring_for_interface__(interface_name, **config)
                    setattr(cls, interface_name, property(fget=p, doc=doc_string))
                    cls._existing_properties_to_interfaces.append(unique_interface_name)
                else:
                    pass

    @classmethod
    def __get_docstring_user_output__(cls):
        line = "This actor has the following output:"
        underline = "~" * len(line)
        docstring = f"{line}\n{underline}\n\n"
        for p in cls._existing_properties_to_interfaces:
            docstring += getattr(cls, p).__doc__
            docstring += "\n"
        return docstring

    def __init__(self, *args, **kwargs):
        GateObject.__init__(self, *args, **kwargs)
        # this is set by the actor engine during initialization
        self.actor_engine = None
        self.user_output = Box()
        self.interfaces_to_user_output = Box()
        self._init_user_output_instance()

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

    def configure_like(self, other_obj):
        super().configure_like(other_obj)
        # also pick up the configuration of the user output
        for k, v in self.user_output.items():
            v.configure_like(other_obj.user_output[k])

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

    @property
    @shortcut_for_single_output_actor
    def keep_data_per_run(self):
        return list(self.interfaces_to_user_output.values())[0].keep_data_per_run

    @keep_data_per_run.setter
    def keep_data_per_run(self, keep_data_per_run):
        for k, v in self.interfaces_to_user_output.items():
            v.keep_data_per_run = keep_data_per_run

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

    def _init_user_output_instance(self):
        for output_name, actor_output_class in self._user_output_classes.items():
            # try:
            #     actor_output_class = self._user_output_classes[output_name]
            # except KeyError:
            #     raise GateImplementationError(
            #         f"In actor {self.type_name}: "
            #         f"No entry 'actor_output_class' specified "
            #         f"in ._user_output_classes for user_output {output_name}."
            #     )
            try:
                interfaces = actor_output_class.__interfaces__
            except AttributeError:
                raise GateImplementationError(f"Special variable __interfaces__ not filled in actor output class {actor_output_class}. ")
            # interfaces = output_config.get("interfaces", None)
            self._add_user_output(actor_output_class, output_name)
            for interface_name, interface_config in interfaces.items():
                interface_params = dict(
                    [(_k, _v) for _k, _v in interface_config.items()]
                )
                try:
                    interface_class = interface_params.pop("interface_class")
                except KeyError:
                    raise GateImplementationError(f"Incorrectly configured interface {interface_name} "
                                                  f"for actor output {output_name}"
                                                  f"in {self.type_name}: No 'interface_class' specified. ")
                self._add_interface_to_user_output(
                    interface_class, output_name, interface_name, **interface_params
                )

    def _add_user_output(
        self,
        actor_output_class,
        name,
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

        self.user_output[name] = actor_output_class(
            name=name,
            simulation=self.simulation,
            belongs_to=self,
            **kwargs,
        )

    def _add_interface_to_user_output(
        self, interface_class, user_output_name, interface_name, **kwargs
    ):
        if interface_name not in self.interfaces_to_user_output:
            self.interfaces_to_user_output[interface_name] = interface_class(
                self, user_output_name, interface_name, **kwargs
            )
        else:
            raise GateImplementationError(
                f"An actor output user interface called '{interface_name}' already exists. "
            )

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


def _get_docstring_for_interface(user_output_class, interface_name, **interface_config):
    docstring = f"**{interface_name}**\n\n"
    docstring += "* This output has the following parameters and methods: \n\n"
    docstring += interface_config["interface_class"].__get_docstring__()
    docstring += "\n"
    docstring += "* Defaults:\n\n"
    defaults = user_output_class.get_user_info_default_values_interface(
        **interface_config
    )
    for k, v in defaults.items():
        docstring += f"  * {k} = {v}\n"
    docstring += "\n"
    return docstring


process_cls(ActorBase)
