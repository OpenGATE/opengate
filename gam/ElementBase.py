import gam
from box import Box
import uuid


## FIXME to rename !! Element can be confused with Material/Element Geant4
## Item ? Component ? SimulationComponent ?

class ElementBase:
    """
        Common class for elements (volume, source or actor)
        Manager a dict (Box) for user parameters: user_info
        Check that all the required keys are provided
    """

    def __init__(self, name=uuid.uuid4().__str__()):
        """
        FIXME
        """
        # create the user info (as a dict Box)
        self.user_info = Box()
        # the type_name *must* be defined in a sub class
        self.user_info.type = self.type_name
        # by default the name is a unique id (uuid)
        if not name:
            name = uuid.uuid4().__str__()
        self.user_info.name = name
        # keep a link to the object in the user info
        self.user_info.object = self
        # list of users keys
        self.required_keys = ['type', 'name', 'object']
        self.simulation = None

    def __del__(self):
        pass

    def __str__(self):
        # FIXME
        s = f'Element: {self.user_info}'
        return s

    def set_simulation(self, simulation):
        self.simulation = simulation

    def initialize_required_keys(self):
        a = list(self.user_info.keys()) + self.required_keys
        self.required_keys = list(dict.fromkeys(a))

    def initialize(self):
        self.check_user_info()

    def check_user_info(self):
        # the list of required keys may be modified in the
        # classes that inherit from this one
        gam.assert_keys(self.required_keys, self.user_info)

        # check potential keys that are ignored
        for k in self.user_info.keys():
            if k not in self.required_keys:
                gam.warning(f'The key "{k}" is ignored in the element : {self.user_info}')
