import opengate_core as g4
import opengate as gate


class ParticleFilter(g4.GateParticleFilter, gate.UserElement):
    type_name = "ParticleFilter"

    def set_default_user_info(user_info):
        gate.UserElement.set_default_user_info(user_info)
        # required user info, default values
        user_info.particle = ""

    def __init__(self, user_info):
        g4.GateParticleFilter.__init__(self)  # no argument in cpp side
        gate.UserElement.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter

    def __getstate__(self):
        # needed to not pickle the g4.GateParticleFilter
        return self.__dict__
