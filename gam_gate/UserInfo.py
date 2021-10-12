import gam_gate as gam


class UserInfo:
    """
        A simple dict that contains the list of user parameters.
        Note that the dict is a Box, allowing simpler access to the keys with a dot
        (rather than brackets)

        The default elements are set with set_default_user_info according to
        the class found thanks to element_type and type_name
    """

    def __init__(self, element_type, type_name, name=None):
        # set the element and the type (it will be checked in get_element_class later)
        # element_type is Volume, Source or Actor
        self.element_type = element_type
        self.type_name = type_name
        # set the name
        self.name = name
        # set the default parameters and values
        cl = gam.get_element_class(element_type, type_name)
        cl.set_default_user_info(self)

    def __str__(self):
        s = f'{self.element_type} {self.name} : {self.__dict__}'
        return s
