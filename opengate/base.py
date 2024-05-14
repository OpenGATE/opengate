import copy
from pathlib import Path

from box import Box
import sys

from .exception import fatal, warning, GateDeprecationError, GateFeatureUnavailableError
from .definitions import (
    __gate_list_objects__,
    __gate_dictionary_objects__,
    __one_indent__,
)
from .decorators import requires_fatal
from .logger import log


# Singletons
class MetaSingletonFatal(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in MetaSingletonFatal._instances:
            MetaSingletonFatal._instances[cls] = super(
                MetaSingletonFatal, cls
            ).__call__(*args, **kwargs)
            return MetaSingletonFatal._instances[cls]
        else:
            fatal(
                f"You are trying to create another instance of {cls.__name__}, but an instance also exists "
                f"in this process. Only one instance per process can be created. "
            )


class GateSingletonFatal(metaclass=MetaSingletonFatal):
    pass


# base class for objects handling user input
class MetaUserInfo(type):
    _created_classes = {}

    def __call__(cls, *args, **kwargs):
        process_cls(cls)
        return super(MetaUserInfo, type(cls)._created_classes[cls]).__call__(
            *args, **kwargs
        )


def process_cls(cls):
    """Digest the class's user_infos and store the augmented class
    in a dictionary inside the metaclass which handles the class creation.
    Example: type(cls) yields the metaclass MetaUserInfo for the class GateObject.
    """
    # check if the class already has an attribute inherited_user_info_defaults
    # cannot use hasattr because it would find the attribute from already processed super classes
    # -> must use __dict__ which contains only attribute of the specific cls object
    if "inherited_user_info_defaults" not in cls.__dict__:
        try:
            # type(cls)._created_classes[cls] = digest_user_info_defaults(cls)
            digest_user_info_defaults(cls)
        except AttributeError:
            fatal(
                "Developer error: Looks like you are calling process_cls on a class "
                "that does not inherit from GateObject."
            )


# Utility function for object creation
def check_property_name(name):
    if len(name.split()) > 1:
        fatal("Invalid property name: f{name}. Should not contain spaces.")


def check_property(property_name, value, defaultvalue):
    msg = (
        lambda required: f"{property_name} requires a {required}, found {type(value).__name__}."
    )
    if isinstance(defaultvalue, str) and not isinstance(value, str):
        raise Exception(msg("string"))
    elif type(defaultvalue) is bool and type(value) is not bool:
        raise Exception(msg("bool"))
    elif type(defaultvalue) is bool and type(value) is bool:
        return
    elif isinstance(defaultvalue, (int, float, complex)) and (
        not isinstance(value, (int, float, complex)) or isinstance(value, bool)
    ):
        raise Exception(msg("number"))


def digest_user_info_defaults(cls):
    inherited_user_info_defaults = {}
    # loop through MRO backwards so that inherited classes
    # are processed first
    for c in cls.mro()[::-1]:
        # check if the class actual define user_info_defaults
        # note: hasattr() would not work because it would yield the attribute from the
        # base class if the inherited class does not define user_info_defaults
        if "user_info_defaults" in c.__dict__:
            # Make sure there are no duplicate user info items.
            if set(c.user_info_defaults).isdisjoint(
                set(inherited_user_info_defaults.keys())
            ):
                inherited_user_info_defaults.update(c.user_info_defaults)
            else:
                fatal(
                    f"Implementation error. "
                    f"Duplicate user info defined for class {cls}."
                    f"Found {c.user_info_defaults}."
                    f"Base classes already contain {inherited_user_info_defaults.keys()}. "
                )
        else:
            # Ensure that the class defines an empty dictionary
            # so that the user_info_defaults from the base class will not show up.
            try:
                setattr(c, "user_info_defaults", {})
            except TypeError:
                # TypeError is thrown if the class is 'object'
                pass
    # FIXME: Check if we should actually process all class in the MRO
    # rather than accumulating user info defaults?
    cls = add_properties_to_class(cls, inherited_user_info_defaults)
    cls.inherited_user_info_defaults = inherited_user_info_defaults
    make_docstring(cls, inherited_user_info_defaults)
    return cls


def add_properties_to_class(cls, user_info_defaults):
    """Add user_info defaults as properties to class if not yet present."""
    for p_name, default_value_and_options in user_info_defaults.items():
        _ok = False
        if isinstance(default_value_and_options, tuple):
            if len(default_value_and_options) == 2:
                default_value = default_value_and_options[0]
                options = default_value_and_options[1]
                _ok = True
        if not _ok:
            s = (
                f"*** DEVELOPER WARNING ***"
                f"User info defaults possibly not implemented correctly for class {cls}.\n"
                "The value for each user info item in the user info dictionary \n"
                "should be a tuple where the first item is the default value, \n"
                "and the second item is a (possibly empty) dictionary of options.\n"
            )
            fatal(s)
        if "deprecated" not in options:
            if not hasattr(cls, p_name):
                check_property_name(p_name)
                setattr(cls, p_name, _make_property(p_name, options=options))

                try:
                    expose_items = options["expose_items"]
                except KeyError:
                    expose_items = False
                if expose_items is True:
                    # expose_items can only be used on dictionary-type user infos
                    # try to get keys and fail of impossible (=not dict type)
                    try:
                        for item_name, item_default_value in default_value.items():
                            check_property_name(item_name)
                            if not hasattr(cls, item_name):
                                setattr(
                                    cls,
                                    item_name,
                                    _make_property(item_name, container_dict=p_name),
                                )
                            else:
                                fatal(
                                    f"Duplicate user info {item_name} defined for class {cls}. Check also base classes or set 'expose_items=False."
                                )
                    except AttributeError:
                        fatal(
                            "Option 'expose_items=True' not available for default_user_info {p_name}."
                        )
    return cls


def _make_property(property_name, options=None, container_dict=None):
    """Return a property that stores the user_info item in a
    dictionary which is an attribute of the object (self).

    """

    if options is None:
        options = {}

    @property
    def prop(self):
        if container_dict is None:
            if "getter_hook" in options:
                return options["getter_hook"](self, self.user_info[property_name])
            else:
                return self.user_info[property_name]
        else:
            return self.user_info[container_dict][property_name]

    try:
        read_only = options["read_only"]
    except KeyError:
        read_only = False
    if read_only is False:

        @prop.setter
        def prop(self, value):
            if "deactivated" in options and options["deactivated"] is True:
                if value != self.inherited_user_info_defaults[property_name][0]:
                    raise GateFeatureUnavailableError(
                        f"The user input parameter {property_name} "
                        f"is currently deactivated and cannot be set."
                    )
            if "deprecated" in options:
                raise GateDeprecationError(options["deprecated"])
            if container_dict is None:
                if "setter_hook" in options:
                    value_to_be_set = options["setter_hook"](self, value)
                else:
                    value_to_be_set = value
                if "allowed_values" in options:
                    if value_to_be_set not in options["allowed_values"]:
                        fatal(
                            f"Object {self.name} received illegal value {value_to_be_set} "
                            f"for user input {property_name}. Allow values are: {options['allowed_values']}."
                        )
                self.user_info[property_name] = value_to_be_set
            else:
                self.user_info[container_dict][property_name] = value

    return prop


def make_docstring(cls, user_info_defaults):
    indent = 4 * " "
    if cls.__doc__ is not None:
        docstring = cls.__doc__
        docstring += "\n"
    else:
        docstring = ""
    docstring += 20 * "*" + "\n\n"
    docstring += (
        "This class has the following user input parameters and default values:\n\n"
    )
    for k, v in user_info_defaults.items():
        default_value = v[0]
        options = v[1]
        docstring += f"{k}"
        if "deprecated" in options:
            docstring += " -> DEPRECATED\n"
            docstring += indent
            docstring += "Info: "
            docstring += options["deprecated"]
            docstring += "\n"
        else:
            if "required" in options and options["required"] is True:
                docstring += " (must be provided)"
            docstring += ":\n"
            # docstring += (20 - len(k)) * " "
            docstring += f"{indent}Default value: {default_value}\n"
            if "allowed_values" in options:
                docstring += f"{indent}Allowed values: {options['allowed_values']}\n"
            if "doc" in options:
                docstring += indent
                docstring += options["doc"]
                docstring += "\n"
        docstring += "\n"
    docstring += 20 * "*"
    docstring += "\n"
    cls.__doc__ = docstring


def restore_userinfo_properties(cls, attributes):
    # In the context of sub-processing and pickling,
    # the following line makes sure the class is processed by the function
    # which sets handles the user_info definitions
    # before the class is used to create a new object instance.
    # Otherwise, the new instance would lack the user_info properties.
    process_cls(cls)
    # this is just conventional unpickling logic:
    obj = cls.__new__(cls)
    obj.__dict__.update(attributes)
    return obj


# class GateObject(metaclass=MetaUserInfo):
class GateObject:
    """This is the base class used for all objects that handle user input in GATE.

    The class is assumed to be processed by process_cls(), either explicitly
    or via the metaclass MetaUserInfo, before any instances of the class are created.
    Some class attributes, e.g. inherited_user_info_defaults, are created as part of this processing.
    """

    user_info_defaults = {"name": (None, {"required": True})}

    def __new__(cls, *args, **kwargs):
        process_cls(cls)
        new_instance = super(GateObject, cls).__new__(cls)
        return new_instance

    def __init__(self, *args, simulation=None, **kwargs):
        self.simulation = None
        if simulation is not None:
            self.simulation = simulation
        # prefill user info with defaults
        self.user_info = Box(
            [
                (k, copy.deepcopy(v[0]))
                for k, v in self.inherited_user_info_defaults.items()
            ]
        )
        # now iterate over them and check if kwargs provide user-specific values
        for k, v in self.inherited_user_info_defaults.items():
            default_value = v[0]
            options = v[1]
            # print(f"current inherited user info: {k}")
            if k in kwargs:
                # print("    ... is in kwargs")
                # if "check_func" in options.keys():
                #     user_info_value = options["check_func"](kwargs[k])
                # else:
                user_info_value = kwargs[k]
                # check_property(k, user_info_value, default_value)
                if "setter_hook" in options:
                    user_info_value = options["setter_hook"](self, user_info_value)
                self.user_info[k] = user_info_value
                kwargs.pop(k)
            else:
                # print("    ... is NOT in kwargs")
                if "required" in options.keys() and options["required"] is True:
                    fatal(
                        f"No value provided for argument '{k}', but required when constructing a {type(self).__name__} object."
                    )
        mro = type(self).__mro__
        parent = mro[mro.index(__class__) + 1]
        # print(f"next class in line is: {parent}")
        # print(f"args at this point: {args}")
        # print(f"kwargs at this point: {kwargs}")
        if type(parent).__name__ != "pybind11_type":
            # print("next class is NOT a pybind class ... ")
            try:
                super().__init__(*args, **kwargs)
            except TypeError as e:
                raise TypeError(
                    f"There was a problem "
                    f"while trying to create the {type(self).__name__} called {self.name}. "
                    f"Check if you have provided unknown keyword arguments. "
                    f"The user input parameters of {type(self).__name__} are: "
                    f"{list(self.inherited_user_info_defaults.keys())}.\n"
                    f"The original exception message was: {e}."
                )
        # else:
        #     print("next class IS a pybind class -> do not call parent class")

    def __str__(self):
        ret_string = (
            f"***\n"
            f"{type(self).__name__} named {self.name} "
            f"with the following parameters:\n"
        )
        for k, v in self.user_info.items():
            if k != "name":
                ret_string += f"{__one_indent__}{k}:\n{2 * __one_indent__}{v}\n"
        ret_string += "***\n"
        return ret_string

    def __getstate__(self):
        """Method needed for pickling. May be overridden in inheriting classes."""
        if self.simulation is not None and self.simulation.verbose_getstate:
            warning(
                f"__getstate__() called in object '{self.name}' of type {type(self).__name__}."
            )
        return self.__dict__

    def __setstate__(self, d):
        """Method needed for pickling. May be overridden in inheriting classes."""
        self.__dict__ = d

    def __reduce__(self):
        """This method is called when the object is pickled.
        Usually, pickle works well without this custom __reduce__ method,
        but objects handling user_infos need a custom __reduce__ to make sure
        the properties linked to the user_infos are properly created as per the meta class

        The return arguments are:
        1) A callable used to create the instance when unpickling
        2) A tuple of arguments to be passed to the callable in 1
        3) The dictionary of the object's properties to be passed to the __setstate__ method (if defined)
        """
        state_dict = self.__getstate__()
        return (
            restore_userinfo_properties,
            (self.__class__, state_dict),
            state_dict,
        )

    def __setattr__(self, key, value):
        # raise an error if the user tries to set an attributed
        # associated with a deprecated user input parameter
        if not hasattr(self, key):
            try:
                raise GateDeprecationError(
                    self.inherited_user_info_defaults[key][1]["deprecated"]
                )
            except KeyError:
                super().__setattr__(key, value)
        else:
            super().__setattr__(key, value)

    @property
    def type_name(self):
        return str(type(self).__name__)

    def close(self):
        """Dummy implementation for inherited classes which do not implement this method."""
        if "simulation" in self.__dict__ and self.simulation is not None:
            if self.simulation.verbose_close:
                warning(
                    f"close() called in object '{self.name}' of type {type(self).__name__}."
                )
        pass

    def release_g4_references(self):
        """Dummy implementation for inherited classes which do not implement this method."""
        pass

    def copy_user_info(self, other_obj):
        for k in self.user_info.keys():
            if k not in ["name", "_name"]:
                try:
                    self.user_info[k] = other_obj.user_info[k]
                except KeyError:
                    pass

    def to_dictionary(self):
        d = {
            "user_info": {},
            "object_type": str(type(self).__name__),
            "object_type_full": str(type(self)),
            "class_module": type(self).__module__,
            "i_am_a_gate_object": True,
        }
        for k, v in self.user_info.items():
            d["user_info"][k] = recursive_userinfo_to_dict(v)
        return d

    def from_dictionary(self, d):
        try:
            if d["object_type_full"] != str(type(self)):
                fatal(
                    f"Error while populating object named {self.name}: "
                    f"Incompatible dictionary associated with object type {d['object_type']}"
                )
        except KeyError:
            fatal(
                f"Error while populating object named {self.name}: "
                "The provided dictionary does not contain any info about the object type."
            )
        for k in self.user_info.keys():
            if k in d["user_info"]:
                if hasattr(self, k):
                    # get the class property associate with the user info end check if it has a setter
                    # otherwise, it is read-only
                    if getattr(type(self), k).fset is not None:
                        setattr(self, k, d["user_info"][k])
                else:
                    warning(
                        f"Could not find user info {k} while populating object {self.name} of type {type(self).__name__} from dictionary."
                    )


class DynamicGateObject(GateObject):
    user_info_defaults = {
        "dynamic_params": (
            None,
            {
                "doc": "List of dictionaries, where each dictionary specifies how the parameters "
                "of this object should evolve over time during the simulation. "
                "If None, the object is static (default).",
                "read_only": True,
            },
        )
    }

    @property
    def is_dynamic(self):
        if self.dynamic_params is None:
            return False
        elif len(self.dynamic_params) == 0:
            return False
        else:
            return True

    @property
    def dynamic_user_info(self):
        return [
            k
            for k in self.user_info
            if "dynamic" in self.inherited_user_info_defaults[k][1]
            and self.inherited_user_info_defaults[k][1]["dynamic"] is True
        ]

    @requires_fatal("simulation")
    def process_dynamic_parametrisation(self, params):
        # create a dictionary to store params which to not correspond to dynamic user info
        # i.e. extra parameters for auxiliary purpose
        extra_params = {}
        extra_params["auto_changer"] = params.pop(
            "auto_changer", True
        )  # True of key not found (default)
        if extra_params["auto_changer"] not in (False, True):
            fatal(
                f"Received wrong value type for 'auto_changer': got {type(extra_params['auto_changer'])}, "
                f"expected: True or False."
            )
        for k in set(params).difference(set(self.dynamic_user_info)):
            extra_params[k] = params.pop(k)
        # apply params which are functions to the timing intervals of the simulation to get the sample quantities
        for k, v in params.items():
            if callable(v):
                params[k] = v(self.simulation.run_timing_intervals)
        # check that the length of all parameter lists match the simulation's timing intervals
        params_with_incorrect_length = []
        for k, v in params.items():
            if len(v) != len(self.simulation.run_timing_intervals):
                params_with_incorrect_length.append((k, len(v)))
        if len(params_with_incorrect_length) > 0:
            s = (
                f"The length of the following dynamic parameters "
                f"does not match the number of timing intervals of the simulation:\n"
            )
            for p in params_with_incorrect_length:
                s += f"{p[0]}: {p[1]}\n"
            s += (
                f"The simulation's timing intervals are: {self.simulation.run_timing_intervals} and "
                f"can be adjusted via the simulation parameter 'run_timing_intervals'. "
            )
            fatal(s)
        return params, extra_params

    def _add_dynamic_parametrisation_to_userinfo(self, params, name):
        """This base class implementation only acts as a setter.
        Classes inheriting from this class should implement an
        add_dynamic_parametrisation() method which actually does something
        with the parameters and then call super().add_dynamic_parametrisation().
        Inheriting classes should avoid calling this method directly.
        """
        if name not in self.user_info["dynamic_params"]:
            self.user_info["dynamic_params"][name] = params
        else:
            fatal(
                f"A dynamic parametrisation with name {name} already exists in volume '{self.name}'."
            )

    def add_dynamic_parametrisation(self, name=None, **params):
        if self.user_info["dynamic_params"] is None:
            self.user_info["dynamic_params"] = {}
        processed_params, extra_params = self.process_dynamic_parametrisation(params)
        processed_params["extra_params"] = extra_params
        # if user provided no name, create one
        if name is None:
            name = f"parametrisation_{len(self.dynamic_params)}"
        self._add_dynamic_parametrisation_to_userinfo(processed_params, name)
        # issue debugging message
        s = f"Added the following dynamic parametrisation to {type(self).__name__} '{self.name}': \n"
        for k, v in processed_params.items():
            s += f"{k}: {v}\n"
        log.debug(s)

    def create_changers(self):
        # this base class implementation is here to keep inheritance intact.
        return []


# DICTIONARY HANDLING


class GateUserInputSwitchDict(Box):
    """
    NOT USED YET!

    Specialized version of a Box (dict) to represent a dictionary with boolean switches.

    The switches handled by the object need to be defined when the object is created
    via a dictionary passed as argument 'default_switches'.
    No switches can be added later, nor can switches be removed.
    Switch values are automatically converted to Bool if possible.
    """

    def __init__(self, default_switches, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._switches = tuple(default_switches.keys())
        for k, v in default_switches.items():
            self[k] = v

    def __setitem__(self, key, value):
        # Do not allow setting entries under the key '_switches' which is used as special attribute
        if key == "_switches":
            raise KeyError(f"Keyword '_switches' is not allowed.")
        # only try setting the item if the key is known
        elif key in self._switches:
            try:
                value_bool = bool(value)
            except ValueError:
                raise ValueError(
                    "You must provide a boolean (or compatible) input, i.e. True or False."
                )
            super().__setitem__(key, value_bool)
        else:
            raise KeyError(
                "You cannot add additional switches. You can only turn on/off existing switches."
            )

    def __delitem__(self, key):
        """The 'del' operator applied on items is blocked so no entries can be removed."""
        raise NotImplementedError("You cannot remove switches.")

    def __setattr__(self, key, value):
        """Make sure to by-pass the __setattr__ method from the Box class for the key '_switches'
        because Box would otherwise turn this into an entry in self, but we want it to be a pure attribute.
        """
        if key == "_switches":
            object.__setattr__(self, key, value)
        else:
            super().__setattr__(key, value)


def recursive_userinfo_to_dict(obj):
    """Walk recursively across entries of user_info and convert to appropriate structure.
    Dictionary-like structures are mapped to dictionary and walked across recursively.
    List-like structures are mapped to lists and walked across recursively.
    GateObject-like objects are converted through their to_dictionary() method.
    All other input (presumably common data types including numpy structures) is left untouched.
    """

    if isinstance(obj, __gate_dictionary_objects__):
        ret = {}
        for k, v in obj.items():
            ret[k] = recursive_userinfo_to_dict(v)
    elif isinstance(obj, __gate_list_objects__):
        ret = []
        for e in obj:
            ret.append(recursive_userinfo_to_dict(e))
    elif isinstance(obj, (GateObject)):
        ret = obj.to_dictionary()
    else:
        ret = obj
    return ret


def find_paths_in_gate_object_dictionary(go_dict, only_input_files=False):
    paths = []
    for ui_name, ui in go_dict["user_info"].items():
        new_paths = find_all_paths(ui)
        if only_input_files is True:
            options = _get_user_info_options(
                ui_name, go_dict["object_type"], go_dict["class_module"]
            )
            try:
                consider_this = options["is_input_file"]
            except KeyError:
                consider_this = False
        else:
            consider_this = True
        if consider_this is True:
            paths.extend(new_paths)
    return paths


def recursively_search_object(obj, condition=(lambda x: True)):
    found_objects = []
    if condition(obj) is True:
        found_objects.append(obj)
    if isinstance(obj, __gate_dictionary_objects__):
        for v in obj.values():
            found_objects.extend(recursively_search_object(v, condition=condition))
    if isinstance(obj, __gate_list_objects__):
        for e in obj:
            found_objects.extend(recursively_search_object(e, condition=condition))
    return found_objects


def find_all_gate_objects(dct):
    def condition(obj):
        try:
            ret = obj["i_am_a_gate_object"]
        except (KeyError, TypeError, IndexError):
            ret = False
        return ret

    return recursively_search_object(dct, condition=condition)


def find_all_paths(dct):
    def condition(obj):
        return isinstance(obj, (Path))

    return recursively_search_object(dct, condition=condition)


def _get_user_info_options(user_info_name, object_type, class_module):
    """Utility function to retrieve the options associated with a user info given the class name,
    the module in which the class is defined, and the name of the user info.
    """

    try:
        options = getattr(
            sys.modules[class_module], object_type
        ).inherited_user_info_defaults[user_info_name][1]
    except KeyError:
        fatal(f"Could not find user info {user_info_name} in {object_type}. ")
    return options


def create_gate_object_from_dict(dct):
    """Function to (re-)create an object derived from GateObject based on a dictionary.

    Used as part of the deserialization chain, when reading simulations stored as JSON file.
    """
    if not "class_module" in dct:
        fatal(
            f"Error while trying to create GateObject from dictionary: Incompatible dictionary"
        )
    obj = getattr(sys.modules[dct["class_module"]], dct["object_type"])(
        name=dct["user_info"]["name"]
    )
    return obj
