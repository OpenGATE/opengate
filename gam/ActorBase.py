import gam


class ActorBase:
    """
    TODO
    """

    def __init__(self, actor_info):
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

    def initialize(self):
        gam.assert_keys(self.required_keys, self.user_info)
