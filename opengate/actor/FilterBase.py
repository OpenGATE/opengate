import opengate as gate


class FilterBase(gate.UserElement):
    """
    Store user information about a filter
    """

    @staticmethod
    def set_default_user_info(user_info):
        gate.UserElement.set_default_user_info(user_info)
        # no user properties for all filters (maybe later)

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from FilterBase
        super().__init__(user_info)

    def __del__(self):
        pass

    def __str__(self):
        s = f"str FilterBase {self.user_info.name} of type {self.user_info.type_name}"
        return s
