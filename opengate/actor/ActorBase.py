import opengate as gate


class ActorBase(gate.UserElement):
    """
    Store user information about an actor
    """

    @staticmethod
    def set_default_user_info(user_info):
        gate.UserElement.set_default_user_info(user_info)
        # user properties shared for all actors
        user_info.mother = gate.__world_name__
        user_info.filters = []
        user_info.priority = 100

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from ActorBase
        super().__init__(user_info)

    def __del__(self):
        pass

    def initialize(self):
        # 'l' must be self to avoid being deleted
        self.l = []
        for f in self.user_info.filters:
            e = gate.new_element(f, self.simulation)
            e.Initialize(f.__dict__)
            self.l.append(e)
        # this is a copy (append cannot be used because fFilters is a std::vector)
        self.fFilters = self.l

    def __str__(self):
        s = f"str ActorBase {self.user_info.name} of type {self.user_info.type_name}"
        return s
