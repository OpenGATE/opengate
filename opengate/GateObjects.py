import copy
import opengate as gate


# META CLASSES
class MetaUserInfo(type):
    _created_classes = {}

    def __call__(cls, *args, **kwargs):
        if cls not in MetaUserInfo._created_classes:
            user_info_defaults = digest_user_info_defaults(cls)
            MetaUserInfo._created_classes[cls] = user_info_defaults
            cls.user_info_defaults = user_info_defaults
            make_docstring(cls, user_info_defaults)
        return super(MetaUserInfo, cls).__call__(
            MetaUserInfo._created_classes[cls], *args, **kwargs
        )


class MetaUserInfoSingleton(type):
    _instances = {}
    _created_classes = {}

    def __call__(cls, *args, **kwargs):
        user_info_defaults = {}
        # loop through MRO backwards so that inherited classes
        # override potential user_info_defaults from parent clases
        if cls not in MetaUserInfo._created_classes:
            user_info_defaults = digest_user_info_defaults(cls)
            MetaUserInfo._created_classes[cls] = user_info_defaults

        if cls not in MetaUserInfoSingleton._instances:
            MetaUserInfoSingleton._instances[cls] = super(
                MetaUserInfoSingleton, cls
            ).__call__(MetaUserInfo._created_classes[cls], *args, **kwargs)
        return MetaUserInfoSingleton._instances[cls]


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
    elif isinstance(defaultvalue, (int, float, complex)) and (
        not isinstance(value, (int, float, complex)) or isinstance(value, bool)
    ):
        raise Exception(msg("number"))


def digest_user_info_defaults(cls):
    user_info_defaults = {}
    # loop through MRO backwards so that inherited classes
    # override potential user_info_defaults from parent clases
    for c in cls.mro()[::-1]:
        try:
            user_info_defaults.update(c.user_info_defaults)
        except AttributeError:
            continue
    add_properties_to_class(cls, user_info_defaults)
    return user_info_defaults


def add_properties_to_class(cls, user_info_defaults):
    """Add user_info defaults as properties to class if not yet present."""
    for p_name, d_value in user_info_defaults.items():
        check_property_name(p_name)
        if not hasattr(cls, p_name):
            # print(f'Adding property {p_name}.')
            setattr(cls, p_name, make_property(p_name, d_value))


def make_property(property_name, default_value):
    """Return a property that stores the user_info item in a
    dictionary which is an attribute of the object (self).

    """

    @property
    def prop(self):
        return self.user_info[property_name]

    @prop.setter
    def prop(self, value):
        check_property(property_name, value, default_value)
        self.user_info[property_name] = value

    return prop


def make_docstring(cls, user_info_defaults):
    if cls.__doc__ is not None:
        docstring = cls.__doc__
        docstring += "\n"
    else:
        docstring = ""
    docstring += 20 * "*" + "\n\n"
    docstring += "This class has the following user parameters and defaults:\n\n"
    for k, v in user_info_defaults.items():
        default_value = v[0]
        parameters = v[1]
        docstring += f"{k}:"
        docstring += (15 - len(k)) * " "
        docstring += f"{v[0]}"
        if "required" in parameters and parameters["required"] is True:
            docstring += "  (must be provided)"
        docstring += "\n"
        if "doc" in parameters:
            docstring += parameters["doc"]
        docstring += "\n"
    docstring += 20 * "*"
    docstring += "\n"
    cls.__doc__ = docstring


def attach_methods(GateObjectClass):
    """Convenience function to avoid redundant code.
    Can be used to add common methods to classes
    that differ otherwise, e.g. GateObject and GateObjectSingleton.

    """

    def __new__(cls, user_info_defaults, *args, **kwargs):
        new_instance = super(GateObjectClass, cls).__new__(cls)
        new_instance.user_info_defaults = user_info_defaults
        return new_instance

    def __init__(self, *args, **kwargs):
        self.user_info = {}
        for k in self.user_info_defaults.keys():
            param_dict = self.user_info_defaults[k][1]
            default_value = self.user_info_defaults[k][0]
            if k in kwargs:
                user_info_value = kwargs[k]
                check_property(k, user_info_value, default_value)
                kwargs.pop(k)
            else:
                if "required" in param_dict.keys() and param_dict["required"] is True:
                    gate.fatal(f"user_info for {k} not provided, but required.")
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

    GateObjectClass.__new__ = __new__
    GateObjectClass.__init__ = __init__
    GateObjectClass.__str__ = __str__
    GateObjectClass.__eq__ = __eq__


# GateObject classes
class GateObjectSingleton(metaclass=MetaUserInfoSingleton):
    user_info_defaults = {"name": (None, {"required": True})}


attach_methods(GateObjectSingleton)


class GateObject(metaclass=MetaUserInfo):
    user_info_defaults = {"name": (None, {"required": True})}


attach_methods(GateObject)
