from ..userelement import UserElement
from ..helpers import warning


class FilterBase(UserElement):
    """
    Store user information about a filter
    """

    element_type = "Filter"

    @staticmethod
    def set_default_user_info(user_info):
        UserElement.set_default_user_info(user_info)
        # no user properties for all filters (maybe later)

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from FilterBase
        super().__init__(user_info)

    def __del__(self):
        pass

    def __str__(self):
        s = f"str FilterBase {self.user_info.name} of type {self.user_info.type_name}"
        return s

    def close(self):
        if self.verbose_close:
            warning(
                f"Closing ParticleFilter {self.user_info.type_name} {self.user_info.name}"
            )

    def __getstate__(self):
        if self.verbose_getstate:
            warning(
                f"getstate ParticleFilter {self.user_info.type_name} {self.user_info.name}"
            )
