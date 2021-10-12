import gam_gate as gam
from box import Box
import uuid


class UserElement:
    """
        Common class for all types of elements (volume, source or actor)
        Manager a dict (Box) for user parameters: user_info
        Check that all the required keys are provided
    """

    def __init__(self, user_info):  # fixme set simulation ?
        # set the user info (a kind of dict)
        self.user_info = user_info
        # check everything is there (except for solid building)
        self.check_user_info()
        # check type_name
        if self.user_info.type_name != self.type_name:
            gam.fatal(f'Error, the type_name inside the user_info is different '
                      f'from the type_name of the class: {self.user_info} in the '
                      f'class {self.__name__} {self.type_name}')
        # by default the name is a unique id (uuid)
        if not self.user_info.name:
            gam.fatal(f'Error a {self.user_info.volume_type} must have '
                      f'a valid name, while it is {self.user_info.name}')

    @staticmethod
    def set_default_user_info(user_info):
        # Should be overwritten by subclass
        pass

    def __del__(self):
        pass

    def __str__(self):
        s = f'Element: {self.user_info}'
        return s

    def set_simulation(self, simulation):  # FIXME to remove (old_
        self.simulation = simulation

    def check_user_info(self):
        # get a fake ui to compare
        ref_ui = gam.UserInfo(self.user_info.element_type, self.user_info.type_name)
        # if this is a solid, we do not check some keys (mother, translation etc)
        if 'i_am_a_solid' in self.user_info.__dict__:
            gam.VolumeManager._pop_keys_unused_by_solid(ref_ui)
        for val in ref_ui.__dict__:
            if val not in self.user_info.__dict__:
                gam.fatal(f'Cannot find "{val}" in {self.user_info}')
        for val in self.user_info.__dict__:
            # special case for solid, and boolean
            if val == 'i_am_a_solid' or val == 'solid':
                continue
            if val == 'nodes' or val == 'add_node':
                continue
            if val not in ref_ui.__dict__.keys():
                gam.warning(f'Unused param "{val}" in {self.user_info}')
