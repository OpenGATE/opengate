import opengate as gate


class ActorManager:
    """
    Manage all the actors in the simulation
    """

    def __init__(self, simulation):
        self.simulation = simulation
        self.user_info_actors = {}

    def __str__(self):
        v = [v.name for v in self.user_info_actors.values()]
        s = f'{" ".join(v)} ({len(self.user_info_actors)})'
        return s

    def __del__(self):
        # print("del ActorManager")
        pass

    def __getstate__(self):
        # needed to not pickle. Need to reset user_info_actors to avoid to store the actors
        self.user_info_actors = {}
        return self.__dict__

    def dump(self):
        n = len(self.user_info_actors)
        s = f"Number of Actors: {n}"
        for actor in self.user_info_actors.values():
            if n > 1:
                a = "\n" + "-" * 20
            else:
                a = ""
            a += f"\n {actor}"
            s += gate.indent(2, a)
        return s

    def get_actor_user_info(self, name):
        if name not in self.user_info_actors:
            gate.fatal(
                f"The actor {name} is not in the current "
                f"list of actors: {self.user_info_actors}"
            )
        return self.user_info_actors[name]

    def add_actor(self, actor_type, name):
        # check that another element with the same name does not already exist
        gate.assert_unique_element_name(self.user_info_actors, name)
        # build it
        a = gate.UserInfo("Actor", actor_type, name)
        # append to the list
        self.user_info_actors[name] = a
        # return the info
        return a
