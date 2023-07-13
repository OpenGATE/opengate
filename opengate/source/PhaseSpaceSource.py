from .SourceBase import *
import opengate_core as g4
from .PhaseSpaceSourceGenerator import *
from scipy.spatial.transform import Rotation
from box import Box


class PhaseSpaceSource(SourceBase):
    """
    Source of particles from a (root) phase space.
    Read position + direction + energy + weight from the root and use them as event.

    if global flag is True, the position/direction are global, not
    in the coordinate system of the mother volume.
    if the global flag is False, the position/direction are relative
    to the mother volume

    - Timing is not used (yet)
    - NOT ready for multithread (yet)
    - type of particle not read in the phase space but set by user

    """

    type_name = "PhaseSpaceSource"

    @staticmethod
    def set_default_user_info(user_info):
        gate.SourceBase.set_default_user_info(user_info)
        # initial user info
        user_info.phsp_file = None
        user_info.n = 1
        user_info.particle = ""  # FIXME later as key
        # if a particle name is supplied, the particle type is set to it
        # otherwise, information from the phase space is used

        # if global flag is True, the position/direction are global, not
        # in the coordinate system of the mother volume.
        # if the global flag is False, the position/direction are relative
        # to the mother volume
        user_info.global_flag = False
        user_info.batch_size = 10000
        # branch name in the phsp file
        user_info.position_key = "PrePositionLocal"
        user_info.position_key_x = None
        user_info.position_key_y = None
        user_info.position_key_z = None
        user_info.direction_key = "PreDirectionLocal"
        user_info.direction_key_x = None
        user_info.direction_key_y = None
        user_info.direction_key_z = None
        user_info.energy_key = "KineticEnergy"
        user_info.weight_key = "Weight"
        user_info.particle_name_key = "ParticleName"
        user_info.PDGCode_key = "PDGCode"
        # change position and direction of the source
        # position is relative to the stored coordinates
        # direction is a rotation of the stored direction
        user_info.override_position = False
        user_info.override_direction = False
        user_info.position = Box()
        user_info.position.translation = [0, 0, 0]
        user_info.position.rotation = Rotation.identity().as_matrix()
        # user_info.time_key = None # FIXME later

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GatePhaseSpaceSource()

    def __init__(self, user_info):
        super().__init__(user_info)
        self.particle_generator = gate.PhaseSpaceSourceGenerator()

    def initialize(self, run_timing_intervals):
        # initialize the mother class generic source

        gate.SourceBase.initialize(self, run_timing_intervals)
        if self.simulation.use_multithread:
            gate.fatal(
                f"Cannot use phsp source in MT mode for the moment"
                f" (need to create a generator that read the root tree randomly"
            )

        # check user info
        ui = self.user_info
        if ui.position_key_x is None:
            ui.position_key_x = f"{ui.position_key}_X"
        if ui.position_key_y is None:
            ui.position_key_y = f"{ui.position_key}_Y"
        if ui.position_key_z is None:
            ui.position_key_z = f"{ui.position_key}_Z"
        if ui.direction_key_x is None:
            ui.direction_key_x = f"{ui.direction_key}_X"
        if ui.direction_key_y is None:
            ui.direction_key_y = f"{ui.direction_key}_Y"
        if ui.direction_key_z is None:
            ui.direction_key_z = f"{ui.direction_key}_Z"

        # initialize the generator (read the phsp file)
        self.particle_generator.initialize(self.user_info)

        # set the function pointer to the cpp side
        self.g4_source.SetGeneratorFunction(self.particle_generator.generate)
