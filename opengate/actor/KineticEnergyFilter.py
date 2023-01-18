import opengate_core as g4
import opengate as gate
import sys


class KineticEnergyFilter(g4.GateKineticEnergyFilter, gate.UserElement):
    type_name = "KineticEnergyFilter"

    def set_default_user_info(user_info):
        gate.UserElement.set_default_user_info(user_info)
        # required user info, default values
        user_info.energy_min = 0
        user_info.energy_max = sys.float_info.max

    def __init__(self, user_info):
        g4.GateKineticEnergyFilter.__init__(self)  # no argument in cpp side
        gate.UserElement.__init__(self, user_info)
        # type_name MUST be defined in class that inherit from a Filter

    def __getstate__(self):
        # needed to not pickle the g4.GateKineticEnergyFilter
        return self.__dict__
