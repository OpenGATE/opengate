from .exception import fatal, warning


class UserElement:
    """
    Common class for all types of elements (volume, source or actor)
    Manager a dict (Box) for user parameters: user_info
    Check that all the required keys are provided
    """

    def __init__(self, user_info):
        # set the user info (a kind of dict)
        # check everything is there (except for solid building)
        check_user_info(user_info)  # removed to avoid circular import
        # self.check_user_info()
        self.user_info = user_info
        # check type_name
        if self.user_info.type_name != self.type_name:
            fatal(
                f"Error, the type_name inside the user_info is different "
                f"from the type_name of the class: {self.user_info} in the "
                f"class {self.__name__} {self.type_name}"
            )
        # by default the name is a unique id (uuid)
        if not self.user_info.name:
            fatal(
                f"Error a {self.user_info.volume_type} must have "
                f"a valid name, while it is {self.user_info.name}"
            )
        # debug
        self.verbose_getstate = False
        self.verbose_close = False

    @staticmethod
    def set_default_user_info(user_info):
        # Should be overwritten by subclass
        pass

    def __str__(self):
        s = f"Element: {self.user_info}"
        return s

    def set_simulation(self, simulation):
        self.simulation = simulation
        if simulation is not None:
            self.verbose_getstate = self.simulation.verbose_getstate
            self.verbose_close = self.simulation.verbose_close


def check_user_info(user_info):
    # get a fake ui to compare
    from .userinfo import UserInfo

    ref_ui = UserInfo(user_info.element_type, user_info.type_name)
    for val in ref_ui.__dict__:
        if val not in user_info.__dict__:
            fatal(f'Cannot find "{val}" in {user_info}')
    for val in user_info.__dict__:
        if val not in ref_ui.__dict__.keys():
            warning(f'Unused param "{val}" in {user_info}')
