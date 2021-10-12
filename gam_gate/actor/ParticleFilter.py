import gam_g4 as g4
import gam_gate as gam


class ParticleFilter(g4.GamParticleFilter, gam.UserElement):
    type_name = 'ParticleFilter'

    def set_default_user_info(user_info):
        gam.UserElement.set_default_user_info(user_info)
        # required user info, default values
        user_info.particle = ''

    def __init__(self, user_info):
        g4.GamParticleFilter.__init__(self)  # no argument in cpp side
        gam.UserElement.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter
