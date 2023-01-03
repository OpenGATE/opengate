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
        # list of filters for this actor
        self.filters_list = []
        # store the output
        self.actor_output = None

    def __del__(self):
        print("del ActorBase")
        pass

    def __getstate__(self):
        """
        This is important : to get actor's outputs from a simulation run in a separate process,
        the class must be serializable (pickle). The attribute "simulation" should not be
        included in the pickle (do know exactly why), so we remove it first.
        The engines (volume, actor, etc.) and G4 objects are also removed if exists.
        """
        print("getstate actor base", self.user_info.name)
        self.simulation = None
        # do not pickle engines and g4 objects
        for v in self.__dict__:
            if "engine" in v or "g4_" in v:
                self.__dict__[v] = None
        return self.__dict__

    def initialize(self, volume_engine=None):
        self.volume_engine = volume_engine
        # 'l' must be self to avoid being deleted
        self.filters_list = []
        for f in self.user_info.filters:
            e = gate.new_element(f, self.simulation)
            e.Initialize(f.__dict__)
            self.filters_list.append(e)
        # this is a copy to cpp ('append' cannot be used because fFilters is a std::vector)
        self.fFilters = self.filters_list

    def __str__(self):
        s = f"str ActorBase {self.user_info.name} of type {self.user_info.type_name}"
        return s
