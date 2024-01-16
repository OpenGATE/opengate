import opengate as gate
import copy


class UserInfo(object):
    """
    A simple dict that contains the list of user parameters.
    Note that the dict is a Box, allowing simpler access to the keys with a dot
    (rather than brackets)

    The default elements are set with set_default_user_info according to
    the class found thanks to element_type and type_name

    (need to inherit from object to allow jsonpickle)
    """

    def __init__(self, element_type, type_name, name=None):
        # set the element and the type (it will be checked in get_element_class later)
        # element_type is Volume, Source or Actor
        # set the name
        self._name = name
        # set the default parameters and values
        from .element import get_element_class

        cls = get_element_class(element_type, type_name)
        self.element_type = element_type
        self.type_name = type_name
        cls.set_default_user_info(self)

    @property
    def name(self):
        # make 'name' a property make it read_only.
        # user cannot change the name of the object once it is declared
        return self._name

    def __str__(self):
        s = f"{self.element_type} {self.name} : {self.__dict__}"
        return s

    def copy_from(self, ui):
        for att in ui.__dict__:
            if att == "_name":
                continue
            self.__dict__[att] = copy.deepcopy(ui.__dict__[att])

    def initialize_source_before_g4_engine(self, source):
        pass
