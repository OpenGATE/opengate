import gam_gate as gam
import gam_g4 as g4


class MotionVolumeActor(g4.GamMotionVolumeActor, gam.ActorBase):
    """
    Every run, move a volume according to the given translations and rotations.
    """

    type_name = 'MotionVolumeActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        user_info.translations = []
        user_info.rotations = []
        user_info.priority = 10

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamMotionVolumeActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'EndSimulationAction'}
        self.AddActions(actions)

    def __del__(self):
        pass

    def __str__(self):
        s = f'MotionVolumeActor {self.user_info.name}'
        return s

    def initialize(self):
        super().initialize()
        # check translations and rotations
        rt = self.simulation.run_timing_intervals
        ui = self.user_info
        if len(ui.translations) != len(rt):
            gam.fatal(f'Error in actor {ui}. '
                      f'Translations must be the same length than the number of runs. '
                      f'While it is {len(ui.translations)} instead of {len(rt)}')
        if len(ui.rotations) != len(rt):
            gam.fatal(f'Error in actor {ui}. '
                      f'Rotations must be the same length than the number of runs. '
                      f'While it is {len(ui.rotations)} instead of {len(rt)}')
