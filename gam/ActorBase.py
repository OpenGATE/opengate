import gam


class ActorBase:
    """
    TODO
    """

    def __init__(self, simu, actor_info):
        # store the simulation
        self.simu = simu
        # store the user information
        self.user_info = actor_info
        # define the actions that will trigger the actor
        # (this attribute is a vector<string> on the cpp side)
        self.actions = []
        # default required user info
        self.required_keys = {'name', 'type', 'attachedTo'}

    def __str__(self):
        s = f'str ActorBase {self.user_info.name} of type {self.user_info.type}'
        return s

    def add_default_info(self, key, value):
        if key not in self.user_info:
            self.user_info[key] = value
        self.required_keys = self.required_keys | {key}

    def initialize(self):  ## FIXME idem in VolumeBase
        # check required keys
        gam.assert_keys(self.required_keys, self.user_info)
        # check potential keys that are ignored
        for k in self.user_info.keys():
            if k == 'g4_actor':
                continue
            if k not in self.required_keys:
                gam.warning(f'The key "{k}" is ignored in the volume : {self.user_info}')
