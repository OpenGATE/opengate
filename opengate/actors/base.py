from box import Box
from functools import wraps

from ..definitions import __world_name__
from ..exception import fatal, GateImplementationError
from ..base import GateObject, process_cls
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
                for k in self.interfaces_to_user_output:
                    s += f"ACTOR.{k}.{name}\n"
                s += "... where ACTOR is your actor object."
            s += f"You can still use the shortcut {name} to *set* the parameter to *all* outputs of this actor. "
            fatal(s)
        return func(self, *args)

    return _with_check


def make_property_function(interface_name):
    def p(self):
        interface_to_get = interface_name
        return self.interfaces_to_user_output[interface_to_get]

    return p


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

    # this dictionary is filled by the developer in each inheriting actor class
    user_output_config = {}
    # this dictionary is filled automatically during the class manufacturing process triggered by __process_this__
    # Do not redefine this manually!
    _processed_user_output_config = {}

    # private list of property names for interfaces already defined
    # in any actor (assuming all actors inherit from the base class)
    # The list is filled automatically during the class manufacturing process triggered by __process_this__
    # Do not redefine this in inheriting classes!
    _existing_properties_to_interfaces = []

    @classmethod
    def _process_user_output_config(cls):
        # it is important to create a new dictionary for this class
        # because we would otherwise write into the dictionary in the base class
        cls._processed_user_output_config = {}
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
            interfaces_of_this_output = output_config.get("interfaces", "auto")
            # if the GATE developer has not defined any interfaces, we create one automatically
            if interfaces_of_this_output == "auto":
                interface_name = output_name  # use the output name as interface name
                interfaces_of_this_output = {
                    interface_name: {
                        "interface_class": actor_output_class.get_default_interface_class(),
                        "item": 0,
                    }
                }
                # pick up parameters from the output config (where the GATE developer might have put them)
                # and add them to the interface config
                other_parameters = dict(
                    [
                        (k, v)
                        for k, v in output_config.items()
                        if k not in ("actor_output_class", "interfaces")
                    ]
                )
                interfaces_of_this_output[interface_name].update(other_parameters)

            # fill in default values where the developer has not defined any for the interface
            for i_name, config in interfaces_of_this_output.items():
                if "interface_class" not in config:
                    raise GateImplementationError(
                        f"Incorrectly configured interface {i_name} "
                        f"for actor output '{output_name}'"
                        f"in {cls}: No 'interface_class' specified. "
                    )
                interfaces_of_this_output[i_name]["suffix"] = i_name
                defaults = actor_output_class.get_user_info_default_values_interface(
                    **config
                )
                for k, v in defaults.items():
                    if k not in interfaces_of_this_output[i_name]:
                        interfaces_of_this_output[i_name][k] = v

            cls._processed_user_output_config[output_name] = {
                "actor_output_class": actor_output_class,
                "interfaces": interfaces_of_this_output,
            }

    @classmethod
    def __process_this__(cls):
        """This is a specialized version of the class method __process_this__ for actor classes."""
        # process user info defaults as in every GateObject class
        super().__process_user_info_defaults__()
        # do the actor specific class manufacturing
        cls._process_user_output_config()
        cls._create_interface_properties()
        # we generate the docstring only now when the interface properties have been created
        cls.__doc__ = cls.__get_docstring__()

    @classmethod
    def _create_interface_properties(cls):
        cls._existing_properties_to_interfaces = []
        # create properties in the actor class so the user can quickly access the interfaces
        for (
            output_name,
            user_output_config,
        ) in cls._processed_user_output_config.items():
            for interface_name, config in user_output_config["interfaces"].items():
                actor_output_class = user_output_config["actor_output_class"]

                if interface_name in cls._existing_properties_to_interfaces:
                    raise GateImplementationError(
                        f"An interface property with unique name {interface_name} "
                        f"already exists in this class. "
                    )

                # Check if this class already has this property and whether it is associated with an interface.
                if hasattr(cls, interface_name):
                    # before we raise an exception, we check if this property was created by a parent class
                    properties_in_bases = []
                    for c in cls.__bases__:
                        try:
                            properties_in_bases.extend(
                                c._existing_properties_to_interfaces
                            )
                        except AttributeError:
                            continue
                    # if the property was not created by a parent class, it must be another attribute of this class,
                    # and we should not override it. The interface name simply collides with an existing attribute
                    if interface_name not in properties_in_bases:
                        raise GateImplementationError(
                            f"Cannot create the property for interface '{interface_name}'\n"
                            f"associated with output class {actor_output_class} "
                            f"in actor {cls.__name__} \n"
                            f"because a property with that name already exists, "
                            f"but it is not associated with the interface. \n"
                            f"These are the exiting properties: {cls._existing_properties_to_interfaces}\n"
                            f"The developer needs to change the name of the interface "
                            f"(or user_output in case the interface is automatically generated). "
                        )

                doc_string = cls._get_docstring_for_interface(
                    output_name, interface_name
                )
                # we associate the property with this actor
                # Note: this does not yet create the actual interface instance
                #       which will be done only when an actor instance is initialized (__init__)
                setattr(
                    cls,
                    interface_name,
                    property(
                        fget=make_property_function(interface_name), doc=doc_string
                    ),
                )
                cls._existing_properties_to_interfaces.append(interface_name)

    @classmethod
    def __get_user_info_docstring__(cls):
        # This is a specialized version of this method for actors
        # which includes info about the output
        docstring = f"This actor has the following output:\n\n"
        for interface_name in cls._existing_properties_to_interfaces:
            docstring += f"* {interface_name}\n"
        docstring += "\n"
        docstring += super().__get_user_info_docstring__()
        return docstring

    @classmethod
    def _get_docstring_for_interface(cls, output_name, interface_name):
        interface_config = cls._processed_user_output_config[output_name]["interfaces"][
            interface_name
        ]
        actor_output_class = cls._processed_user_output_config[output_name][
            "actor_output_class"
        ]
        docstring = f"**{interface_name}**\n\n"
        docstring += "* Parameters and defaults:\n\n"
        defaults = actor_output_class.get_user_info_default_values_interface(
            **interface_config
        )
        for k, v in defaults.items():
            docstring += f"  * {k} = {v}\n"
        docstring += "\n"
        docstring += "* Methods: \n\n"
        docstring += interface_config["interface_class"].__get_docstring_methods__()
        docstring += "\n"
        docstring += "* Description of the parameters: \n\n"
        docstring += interface_config["interface_class"].__get_docstring_attributes__()
        docstring += "\n"
        return docstring

    def __init__(self, *args, **kwargs) -> None:
        GateObject.__init__(self, *args, **kwargs)
        # the actor engine is set by the actor engine during initialization
        self.actor_engine = None
        self.user_output = Box()
        self.interfaces_to_user_output = Box()
        self._init_user_output_instance()
        # the mother of the volume the actor is attached to will be automatically set
        self.mother_attached_to = None

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
                    filename, v.suffix, suffix_separator="_"
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
        # first, Close the cpp part of the actor
        self.Close()
        # close all outputs
        for uo in self.user_output.values():
            uo.close()
        # remove the g4 objects and the actor engine pointer
        for v in self.__dict__:
            if "g4_" in v:
                self.__dict__[v] = None
        self.actor_engine = None
        # close the base GateObject
        super().close()

    def initialize(self):
        """This base class method initializes common settings and should be called in all inheriting classes."""

        # set the mother of the attached_to volume to the actor
        # but only if attached to a single volume.
        if isinstance(self.attached_to, str):
            vol = self.simulation.volume_manager.get_volume(self.attached_to)
            self.mother_attached_to = vol.mother
            if vol.mother is None:
                # the mother of the world is the world (sic)
                self.mother_attached_to = __world_name__
        else:
            self.mother_attached_to = "None"
        # set the name of the attached_to mother volume to cpp
        self.SetMotherAttachedToVolumeName(self.mother_attached_to)

        any_active = False
        for p in self._existing_properties_to_interfaces:
            interface = getattr(self, p)
            any_active |= interface.active
        if len(self.user_output) > 0 and not any_active:
            self.warn_user(f"The actor {self.name} has no active output. ")

        for k, v in self.user_output.items():
            v.initialize()

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
        for output_name, output_config in self._processed_user_output_config.items():
            try:
                interfaces = output_config["interfaces"]
            except AttributeError:
                raise GateImplementationError(
                    f"No interfaces found for output {output_name}. "
                )
            actor_output_class = output_config["actor_output_class"]
            # get the names of the parameters of this output class
            # we do not need to specify the item (in case the output handles a container)
            # because the names are equal for all data items in the container
            default_params = list(
                actor_output_class.get_user_info_default_values_interface().keys()
            )

            # create and add the instance of the actor output
            self._add_user_output(actor_output_class, output_name)

            # now create the interface instances linking to the actor output
            for interface_name, interface_config in interfaces.items():
                interface_params = dict(
                    [(_k, _v) for _k, _v in interface_config.items()]
                )
                try:
                    interface_class = interface_params.pop("interface_class")
                except KeyError:
                    raise GateImplementationError(
                        f"Incorrectly configured interface {interface_name} "
                        f"for actor output {output_name}"
                        f"in {self.type_name}: No 'interface_class' specified. "
                    )
                self._add_interface_to_user_output(
                    interface_class, output_name, interface_name, **interface_params
                )
                # use the newly created interface to set the defaults
                interface = self.interfaces_to_user_output[interface_name]
                for p in default_params:
                    v = interface_config[p]
                    setattr(interface, p, v)

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
            # set an instance attribute __doc__ for this interface
            # equivalent to the property linking to this interface
            # so that the user gets a meaningful info when using something like
            # ``help(my_dose_actor.dose_uncertainty)
            self.interfaces_to_user_output[interface_name].__doc__ = getattr(
                type(self), interface_name
            ).__doc__
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


process_cls(ActorBase)
