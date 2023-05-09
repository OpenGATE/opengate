from .SourceBase import *
import opengate_core as g4
from .PhaseSpaceSourceGenerator import *


class PhaseSpaceSource(SourceBase):
    """
    FIXME
    """

    type_name = "PhaseSpaceSource"

    @staticmethod
    def set_default_user_info(user_info):
        gate.SourceBase.set_default_user_info(user_info)
        # initial user info
        user_info.phsp_file = None
        user_info.n = 1
        user_info.particle = None  # FIXME later as key ?
        # branch name in the phsp file
        user_info.energy_key = None
        user_info.position_key = None
        user_info.direction_key = None
        user_info.weight_key = None
        # user_info.time_key = None #FIXME later
        user_info.batch_size = 10000

    def __del__(self):
        pass

    def create_g4_source(self):
        print("Create cpp phsp source")
        return g4.GatePhaseSpaceSource()

    def __init__(self, user_info):
        super().__init__(user_info)
        self.particle_generator = gate.PhaseSpaceSourceGenerator()

    def initialize(self, run_timing_intervals):
        print("source initialize")
        # initialize the mother class generic source
        gate.SourceBase.initialize(self, run_timing_intervals)

        # initialize the generator (read the phsp file)
        print("generator initialize")
        self.particle_generator.initialize(self.user_info)

        # set the function pointer to the cpp side
        self.g4_source.SetGeneratorFunction(self.particle_generator.generator)

        # set the parameters to the cpp side
        self.g4_source.SetGeneratorInfo(self.particle_generator.generator_info)
