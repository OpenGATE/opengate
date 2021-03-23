from ..UserElement import *
from gam.VolumeManager import __world_name__


class ActorBase(UserElement):
    """
    Store user information about an actor and the corresponding g4 object
    """

    def __init__(self, name):
        #UserElement.__init__(self, name)
        UserElement.old__init__(self, self.type_name, name)
        # define the actions that will trigger the actor
        # (this attribute is a vector<string> on the cpp side)
        # default required user info
        self.user_info.attached_to = __world_name__
        # FIXME
        self.user_info.element_type = 'Actor'

    def __del__(self):
        pass

    def initialize(self): ## FIXME to remove ?
        pass

    def __str__(self):
        s = f'str ActorBase {self.user_info.name} of type {self.user_info.type}'
        return s
