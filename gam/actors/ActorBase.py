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
        user_info.attached_to = __world_name__

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from ActorBase
        super().__init__(user_info)
        #self.g4_actor = self.create_g4_actor()

    def __del__(self):
        pass

    #def create_g4_actor(self):
    #    gam.fatal(f'the function create_g4_actor must be overwritten')
    #    return None

    def initialize(self):  ## FIXME to remove ?
        pass

    def __str__(self):
        s = f'str ActorBase {self.user_info.name} of type {self.user_info.type}'
        return s
