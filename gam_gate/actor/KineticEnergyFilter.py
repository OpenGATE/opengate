import gam_g4 as g4
import gam_gate as gam
import sys

class KineticEnergyFilter(g4.GamKineticEnergyFilter, gam.UserElement):
    type_name = 'KineticEnergyFilter'

    def set_default_user_info(user_info):
        gam.UserElement.set_default_user_info(user_info)
        # required user info, default values
        user_info.energy_min = 0
        user_info.energy_max = sys.float_info.max

    def __init__(self, user_info):
        g4.GamKineticEnergyFilter.__init__(self)  # no argument in cpp side
        gam.UserElement.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter
