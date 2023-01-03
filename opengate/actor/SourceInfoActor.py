import opengate as gate
import opengate_core as g4
import uproot
import numpy as np


class SourceInfoActor(g4.GateVActor, gate.ActorBase):
    """
    TODO
    """

    type_name = "SourceInfoActor"

    def __init__(self, name):
        g4.GateVActor.__init__(self, self.type_name)
        gate.ActorBase.__init__(self, name)
        # default actions
        self.actions = ["BeginOfRunAction", "EndOfRunAction", "BeginOfEventAction"]
        # parameters
        self.user_info.filename = None
        self.tree = None
        self.file = None
        # FIXME --> do it by batch
        self.positions = []

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)
        if not self.user_info.filename:
            gate.fatal(
                f"Provide a filename to the actor {self.user_info.physics_list_name}"
            )
        # create the root tree
        self.file = uproot.recreate(self.user_info.filename)
        self.file[self.user_info.physics_list_name] = uproot.newtree(
            {
                "position_x": np.float64,
                "position_y": np.float64,
                "position_z": np.float64,
            }
        )
        self.tree = self.file[self.user_info.physics_list_name]
        print(self.tree)

    def BeginOfRunAction(self, run):
        print("Start run SourceInfoActor")

    def EndOfRunAction(self, run):
        print("End run SourceInfoActor")
        print(len(self.positions))
        self.positions = np.array(self.positions)
        self.tree.extend(
            {
                "position_x": self.positions[:, 0],
                "position_y": self.positions[:, 1],
                "position_z": self.positions[:, 2],
            }
        )

    def BeginOfEventAction(self, event):
        p = event.GetPrimaryVertex(0).GetPosition()
        # print('BeginOfEventAction')
        self.positions.append(gate.vec_g4_as_np(p))
