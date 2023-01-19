import opengate as gate
import opengate_core as g4


class MotionVolumeActor(g4.GateMotionVolumeActor, gate.ActorBase):
    """
    Every run, move a volume according to the given translations and rotations.
    """

    type_name = "MotionVolumeActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.translations = []
        user_info.rotations = []
        user_info.priority = 10

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        # check rotations and translation
        u = user_info
        if len(u.translations) != len(u.rotations):
            gate.fatal(
                f"Error, translations and rotations must have the same length, while it is"
                f" {len(u.translations)} and {len(u.rotations)}"
            )
        g4.GateMotionVolumeActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def __del__(self):
        pass

    def __str__(self):
        s = f"MotionVolumeActor {self.user_info.name}"
        return s

    def __getstate__(self):
        # needed to not pickle the G4Transform3D
        gate.ActorBase.__getstate__(self)
        self.user_info.rotations = []
        return self.__dict__

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)
        # check translations and rotations
        rt = self.simulation.run_timing_intervals
        ui = self.user_info
        if len(ui.translations) != len(rt):
            gate.fatal(
                f"Error in actor {ui}. "
                f"Translations must be the same length than the number of runs. "
                f"While it is {len(ui.translations)} instead of {len(rt)}"
            )
        if len(ui.rotations) != len(rt):
            gate.fatal(
                f"Error in actor {ui}. "
                f"Rotations must be the same length than the number of runs. "
                f"While it is {len(ui.rotations)} instead of {len(rt)}"
            )
