import gam
from gam.VolumeManager import __world_name__


class ActorBase(gam.UserElement):
    """
    Store user information about an actor
    """

    @staticmethod
    def set_default_user_info(user_info):
        gam.UserElement.set_default_user_info(user_info)
        # common user properties for all source
        user_info.mother = __world_name__

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from ActorBase
        super().__init__(user_info)

    def __del__(self):
        pass

    def initialize(self):
        pass

    def __str__(self):
        s = f'str ActorBase {self.user_info.physics_list_name} of type {self.user_info.type}'
        return s
