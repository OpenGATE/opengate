import copy
from box import Box

from .exception import fatal


# META CLASSES
class MetaUserInfo(type):
    _created_classes = {}

    def __call__(cls, *args, **kwargs):
        return super(MetaUserInfo, process_cls(cls)).__call__(*args, **kwargs)


class MetaUserInfoSingleton(type):
    _instances = {}
    _created_classes = {}

    def __call__(cls, *args, **kwargs):
        if cls not in MetaUserInfoSingleton._instances:
            MetaUserInfoSingleton._instances[cls] = super(
                MetaUserInfoSingleton, process_cls(cls)
            ).__call__(*args, **kwargs)
        return MetaUserInfoSingleton._instances[cls]


def process_cls(cls):
    """Digest the class's user_infos and store the augmented class
    in a dicitonary inside the meta class which handles the class creation.
    Note: type(cls) yields the meta class MetaUserInfo or MetaUserInfoSingleton,
    depending on the class in question (e.g. GateObject, GateObjectSingleton).
    """
    if cls not in type(cls)._created_classes:
        cls = digest_user_info_defaults(cls)
        type(cls)._created_classes[cls] = cls
    return type(cls)._created_classes[cls]


# Utility function for object creation
def check_property_name(name):
    if len(name.split()) > 1:
        raise Exception(
            "Invalid property name: f{name}. Should not contain spaces."
        ) from None


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
    # override potential user_info_defaults from parent clases
    for c in cls.mro()[::-1]:
        try:
            inherited_user_info_defaults.update(c.user_info_defaults)
        except AttributeError:
            continue
    add_properties_to_class(cls, inherited_user_info_defaults)
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
            default_value = default_value_and_options
            options = {}
            s = (
                f"User info defaults possibly not implemented correctly for class {cls}.\n"
                "The value for each user info item in the user info dictionary \n"
                "should be a tuple where the first item is the default value, \n"
                "and the second item is a (possibly empty) dictionary of options.\n"
            )
            print("*** DEVELOPER WARNING ***")
            print(s)
        check_property_name(p_name)
        if not hasattr(cls, p_name):
            setattr(cls, p_name, make_property(p_name, default_value, options=options))
        else:
            raise Exception(
                f"Duplicate user info {p_name} defined for class {cls}. Check also base classes."
            )

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
                            make_property(
                                item_name, item_default_value, contained_in_dict=p_name
                            ),
                        )
                    else:
                        raise Exception(
                            f"Duplicate user info {item_name} defined for class {cls}. Check also base classes or set 'expose_items=False."
                        )
            except AttributeError:
                raise Exception(
                    "Option 'expose_items=True' not available default user info {p_name}."
                )


def make_property(property_name, default_value, options=None, contained_in_dict=None):
    """Return a property that stores the user_info item in a
    dictionary which is an attribute of the object (self).

    """

    @property
    def prop(self):
        if contained_in_dict is None:
            return self.user_info[property_name]
        else:
            return self.user_info[contained_in_dict][property_name]

    @prop.setter
    def prop(self, value):
        check_property(property_name, value, default_value)
        if contained_in_dict is None:
            self.user_info[property_name] = value
        else:
            self.user_info[contained_in_dict][property_name] = value

    return prop


def make_docstring(cls, user_info_defaults):
    if cls.__doc__ is not None:
        docstring = cls.__doc__
        docstring += "\n"
    else:
        docstring = ""
    docstring += 20 * "*" + "\n\n"
    docstring += "This class has the following user infos and default values:\n\n"
    for k, v in user_info_defaults.items():
        default_value = v[0]
        options = v[1]
        docstring += f"{k}:"
        docstring += (15 - len(k)) * " "
        docstring += f"{v[0]}"
        if "required" in options and options["required"] is True:
            docstring += "  (must be provided)"
        docstring += "\n"
        if "doc" in options:
            docstring += options["doc"]
        docstring += "\n"
    docstring += 20 * "*"
    docstring += "\n"
    cls.__doc__ = docstring


def restore_userinfo_properties(cls, attributes):
    # In the context of subprocessing and pickling,
    # the following line makes sure the class is processed by the function
    # which sets handles the user_info definitions
    # before the class is used to create a new object instance.
    # Otherwise, the new instance would lack the user_info properties.
    cls = process_cls(cls)
    # this is just conventional unpickling logic:
    obj = cls.__new__(cls)
    obj.__dict__.update(attributes)
    return obj


def attach_methods(GateObjectClass):
    """Convenience function to avoid redundant code.
    Can be used to add common methods to classes
    that differ otherwise, e.g. GateObject and GateObjectSingleton.

    """

    def __new__(cls, *args, **kwargs):
        new_instance = super(GateObjectClass, cls).__new__(cls)
        return new_instance

    def __init__(self, *args, **kwargs):
        self.user_info = Box()
        for k, v in self.inherited_user_info_defaults.items():
            default_value = v[0]
            options = v[1]
            if k in kwargs:
                if "check_func" in options.keys():
                    user_info_value = options["check_func"](kwargs[k])
                else:
                    user_info_value = kwargs[k]
                # check_property(k, user_info_value, default_value)
                kwargs.pop(k)
            else:
                if "required" in options.keys() and options["required"] is True:
                    fatal(
                        f"No value provided for argument '{k}', but required when constructing a {type(self).__name__} object."
                    )
                user_info_value = copy.deepcopy(default_value)
            self.user_info[k] = user_info_value
        super(GateObjectClass, self).__init__()

    def __str__(self):
        ret_string = ""
        for k, v in self.user_info.items():
            ret_string += f"{k}: {v}\n"
        return ret_string

    def __eq__(self, other):
        keys_self = set(self.user_info.keys())
        keys_other = set(other.user_info.keys())
        if keys_other != keys_self:
            return False
        keys_self.discard("name")
        for k in keys_self:
            if self.user_info[k] != other.user_info[k]:
                return False
        return True

    def __getstate__(self):
        """Method needed for pickling. Maybe be overridden in inheriting classes."""
        return self.__dict__

    def __setstate__(self, d):
        """Method needed for pickling. Maybe be overridden in inheriting classes."""
        self.__dict__ = d

    def __reduce__(self):
        """This method is called when the object is pickled.
        Usually, pickle works well without this custom __reduce__ method,
        but object handling user_infos need a custom __reduce__ to make sure
        the properties linked to the user_infos are properly created as per the meta class

        The return arguments are:
        1) A callable used to create the instance when unpickling
        2) A tuple of arguments to be passed to the callable in 1
        3) The dictionary of the objects properties to be passed to the __setstate__ method (if defined)
        """
        return (
            restore_userinfo_properties,
            (self.__class__, self.__getstate__()),
            self.__getstate__(),
        )

    GateObjectClass.__new__ = __new__
    GateObjectClass.__init__ = __init__
    GateObjectClass.__str__ = __str__
    GateObjectClass.__eq__ = __eq__
    GateObjectClass.__getstate__ = __getstate__
    GateObjectClass.__setstate__ = __setstate__
    GateObjectClass.__reduce__ = __reduce__


# GateObject classes
class GateObjectSingleton(metaclass=MetaUserInfoSingleton):
    user_info_defaults = {"name": (None, {"required": True})}


attach_methods(GateObjectSingleton)


class GateObject(metaclass=MetaUserInfo):
    user_info_defaults = {"name": (None, {"required": True})}


attach_methods(GateObject)
