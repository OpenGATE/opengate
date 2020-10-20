import gam
from box import Box


class ElementBase:
    """
        Common class for elements (volume, source or actor)
        Manager a dict (Box) for user parameters: user_info
        Check that all the required keys are provided
    """

    def __init__(self, type_name, name):
        """
        FIXME
        """
        # create the user info (as a dict Box)
        self.user_info = Box()
        self.user_info.type = type_name
        self.user_info.name = name
        # list of users keys
        self.required_keys = ['type', 'name']
        self.simulation = None

    def set_simulation(self, simulation):
        self.simulation = simulation

    def initialize_keys(self):
        a = list(self.user_info.keys()) + self.required_keys
        self.required_keys = list(dict.fromkeys(a))

    def __del__(self):
        # for debug
        print('ElementBase destructor')
        pass

    def __str__(self):
        # FIXME
        s = f'Element: {self.user_info}'
        return s

    def check_user_info(self):
        # the list of required keys may be modified in the
        # classes that inherit from this one
        gam.assert_keys(self.required_keys, self.user_info)

        # check potential keys that are ignored
        for k in self.user_info.keys():
            if k not in self.required_keys:
                gam.warning(f'The key "{k}" is ignored in the element : {self.user_info}')
