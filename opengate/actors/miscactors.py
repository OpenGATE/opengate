import uuid
from box import Box
from datetime import datetime
import json
import uproot
import numpy as np
import time
import platform
import opengate_core as g4
from .base import ActorBase
from ..exception import fatal
from ..geometry.utility import rot_np_as_g4, vec_np_as_g4, vec_g4_as_np
from ..utility import g4_units
from ..userinfo import UserInfo
from .actoroutput import ActorOutputBase


class ActorOutputStatisticsActor(ActorOutputBase):
    user_info_defaults = {
        "encoder": (
            "json",
            {
                "doc": "How should the output be encoded?",
                "allowed_values": ("json", "legacy"),
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # predefine the merged_data
        self.merged_data = Box()
        self.merged_data.run_count = 0
        self.merged_data.event_count = 0
        self.merged_data.track_count = 0
        self.merged_data.step_count = 0
        self.merged_data.duration = 0
        self.merged_data.start_time = 0
        self.merged_data.stop_time = 0
        self.merged_data.sim_start_time = 0
        self.merged_data.sim_stop_time = 0
        self.merged_data.init = 0
        self.merged_data.track_types = {}
        self.merged_data.nb_thread = 1

    @property
    def pps(self):
        if self.merged_data.duration != 0:
            return self.merged_data.event_count / self.merged_data.duration
        else:
            return 0

    @property
    def tps(self):
        if self.merged_data.duration != 0:
            return self.merged_data.track_count / self.merged_data.duration
        else:
            return 0

    @property
    def sps(self):
        if self.merged_data.duration != 0:
            return self.merged_data.step_count / self.merged_data.duration
        else:
            return 0

    def store_data(self, data):
        self.merged_data.update(data)

    def get_processed_output(self):
        d = {}
        sec = g4_units.s
        d["runs"] = {"value": self.merged_data.run_count, "unit": None}
        d["events"] = {"value": self.merged_data.event_count, "unit": None}
        d["tracks"] = {"value": self.merged_data.track_count, "unit": None}
        d["steps"] = {"value": self.merged_data.step_count, "unit": None}
        d["init"] = {
            "value": self.merged_data.init / sec,
            "unit": g4.G4BestUnit(self.merged_data.init, "Time"),
        }
        d["duration"] = {
            "value": self.merged_data.duration / sec,
            "unit": g4.G4BestUnit(self.merged_data.duration, "Time"),
        }
        d["pps"] = {"value": self.pps, "unit": g4.G4BestUnit(self.pps, "Time")}
        d["tps"] = {"value": self.tps, "unit": g4.G4BestUnit(self.tps, "Time")}
        d["sps"] = {"value": self.sps, "unit": g4.G4BestUnit(self.sps, "Time")}
        d["start"] = {
            "value": self.merged_data.start,
            "unit": g4.G4BestUnit(self.merged_data.start, "Time"),
        }
        d["stop"] = {
            "value": self.merged_data.stop,
            "unit": g4.G4BestUnit(self.merged_data.stop, "Time"),
        }
        d["sim_start"] = {
            "value": self.merged_data.sim_start,
            "unit": g4.G4BestUnit(self.merged_data.sim_start, "Time"),
        }
        d["sim_stop"] = {
            "value": self.merged_data.sim_stop,
            "unit": g4.G4BestUnit(self.merged_data.sim_stop, "Time"),
        }
        d["threads"] = {"value": self.merged_data.nb_threads, "unit": None}
        d["arch"] = {"value": platform.system(), "unit": None}
        d["python"] = {"value": platform.python_version(), "unit": None}
        d["track_types"] = {"value": self.merged_data.track_types, "unit": None}
        return d

    def __str__(self):
        s = ""
        for k, v in self.get_processed_output():
            if k == "track_types" and len(v["value"]) > 0:
                s += "track_types\n"
                for t, n in v["value"].items():
                    s += f"{' ' * 20}{t}: {n}\n"
            else:
                if v["unit"] is None:
                    unit = ""
                else:
                    unit = str(v["unit"])
                s += f"{k}{' ' * (12 - len(k))}{v['value']} {unit}\n"
        return s

    def write_data(self):
        """Override virtual method from base class."""
        with open(self.get_output_path("merged"), "w+") as f:
            if self.encoder == "json":
                json.dump(self.merged_data, f, indent=4)
            else:
                f.write(self.__str__())


class SimulationStatisticsActor(g4.GateSimulationStatisticsActor, ActorBase):
    """
    Store statistics about a simulation run.
    """

    user_info_defaults = {
        "track_types_flag": (
            False,
            {
                "doc": "Should the type of tracks be counted?",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        # # user_info can be null when create empty actor (that read file)
        # if not user_info:
        #     user_info = UserInfo("Actor", self.type_name, name=uuid.uuid4().__str__())
        ActorBase.__init__(self, *args, **kwargs)
        g4.GateSimulationStatisticsActor.__init__(self, self.user_info)

        self._add_user_output(ActorOutputStatisticsActor, "stats")

        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def __str__(self):
        s = ActorBase.__str__(self)
        s += "***********\n"
        s += "User output\n"
        s += self.user_output["stats"].__str__()
        return s

    def initialize(self):
        ActorBase().initialize()

        self.InitializeUserInput(self.user_info)
        self.ActorInitialize()

    def StartSimulationAction(self):
        g4.GateSimulationStatisticsActor.StartSimulationAction(self)
        self.user_output.stats.nb_threads = self.simulation.number_of_threads

    def EndSimulationAction(self):
        g4.GateSimulationStatisticsActor.EndSimulationAction(self)
        self.user_output.stats.store_data(self.GetCounts())

        if self.simulation is not None:
            sim_start = self.simulation.run_timing_intervals[0][0]
        else:
            sim_start = 0

        if self.simulation is not None:
            sim_stop = self.simulation.run_timing_intervals[-1][1]
        else:
            sim_stop = 0

        self.user_output.stats.store_data(
            {"sim_start": sim_start * g4_units.s, "sim_stop": sim_stop * g4_units.s}
        )
        self.user_output.stats.write_data_if_requested()


"""
    It is feasible to get callback every Run, Event, Track, Step in the python side.
    However, it is VERY time consuming. For SteppingAction, expect large performance drop.
    It could be however useful for prototyping or tests.

    it requires "trampoline functions" on the cpp side.

    # feasible but very slow !
    def SteppingAction(self, step, touchable):
        g4.GateSimulationStatisticsActor.SteppingAction(self, step, touchable)
        do_something()
"""


# class SourceInfoActor(g4.GateVActor, ActorBase):
#     """
#     TODO
#     """
#
#     type_name = "SourceInfoActor"
#
#     def __init__(self, name):
#         g4.GateVActor.__init__(self, self.type_name)
#         ActorBase.__init__(self, name)
#         # default actions
#         self.actions = ["BeginOfRunAction", "EndOfRunAction", "BeginOfEventAction"]
#         # parameters
#         self.user_info.filename = None
#         self.tree = None
#         self.file = None
#         # FIXME --> do it by batch
#         self.positions = []
#
#     def initialize(self, volume_engine=None):
#         super().initialize(volume_engine)
#         if not self.user_info.filename:
#             fatal(f"Provide a filename to the actor {self.user_info.physics_list_name}")
#         # create the root tree
#         self.file = uproot.recreate(self.user_info.filename)
#         self.file[self.user_info.physics_list_name] = uproot.newtree(
#             {
#                 "position_x": np.float64,
#                 "position_y": np.float64,
#                 "position_z": np.float64,
#             }
#         )
#         self.tree = self.file[self.user_info.physics_list_name]
#         print(self.tree)
#
#     def BeginOfRunAction(self, run):
#         print("Start run SourceInfoActor")
#
#     def EndOfRunAction(self, run):
#         print("End run SourceInfoActor")
#         print(len(self.positions))
#         self.positions = np.array(self.positions)
#         self.tree.extend(
#             {
#                 "position_x": self.positions[:, 0],
#                 "position_y": self.positions[:, 1],
#                 "position_z": self.positions[:, 2],
#             }
#         )
#
#     def BeginOfEventAction(self, event):
#         p = event.GetPrimaryVertex(0).GetPosition()
#         # print('BeginOfEventAction')
#         self.positions.append(vec_g4_as_np(p))


# class TestActor(g4.GateVActor, ActorBase):
#     """
#     Test actor: only py side (no cpp)
#     For prototyping (slow)
#     """
#
#     user_info_defaults = {
#         "track_types_flag": (
#             False,
#             {
#                 "doc": "How should the output be encoded?",
#                 "allowed_values": ("json", "legacy"),
#             },
#         ),
#     }
#
#     type_name = "TestActor"
#
#     # @staticmethod
#     # def set_default_user_info(user_info):
#     #     ActorBase.set_default_user_info(user_info)
#     #     user_info.track_types_flag = False
#
#     def __init__(self, *args, **kwargs):
#         ActorBase.__init__(self, *args, **kwargs)
#         g4.GateVActor.__init__(self, self.user_info)
#         self.AddActions({
#             "StartSimulationAction",
#             "EndSimulationAction",
#             "BeginOfEventAction",
#             "EndOfRunAction",
#             "PreUserTrackingAction",
#             "SteppingAction",
#         })
#         # empty results for the moment
#         self.run_count = 0
#         self.event_count = 0
#         self.track_count = 0
#         self.step_count = 0
#         self.duration = 0
#         self.track_types = {}
#         self.start_time = 0
#         self.end_time = 0
#
#     @property
#     def pps(self):
#         sec = g4_units.s
#         if self.duration != 0:
#             return self.event_count / self.duration * sec
#         return 0
#
#     @property
#     def tps(self):
#         sec = g4_units.s
#         if self.duration != 0:
#             return self.track_count / self.duration * sec
#         return 0
#
#     @property
#     def sps(self):
#         sec = g4_units.s
#         if self.duration != 0:
#             return self.step_count / self.duration * sec
#         return 0
#
#     def __str__(self):
#         if not self:
#             return ""
#         s = (
#             f"Runs     {self.run_count}\n"
#             f"Events   {self.event_count}\n"
#             f"Tracks   {self.track_count}\n"
#             f"Step     {self.step_count}\n"
#             f'Duration {g4.G4BestUnit(self.duration, "Time")}\n'
#             f"PPS      {self.pps:.0f}\n"
#             f"TPS      {self.tps:.0f}\n"
#             f"SPS      {self.sps:.0f}"
#         )
#         if self.track_types_flag:
#             s += f"\n" f"Track types: {self.track_types}"
#         return s
#
#     def StartSimulationAction(self):
#         self.start_time = time.time()
#
#     def BeginOfEventAction(self, event):
#         pass
#
#     def PreUserTrackingAction(self, track):
#         self.track_count += 1
#         if self.user_info.track_types_flag:
#             p = track.GetParticleName()
#             try:
#                 self.track_types[p] += 1
#             except:
#                 self.track_types[p] = 1
#
#     def EndOfRunAction(self, run):
#         self.run_count += 1
#         self.event_count += run.GetNumberOfEvent()
#
#     def SteppingAction(self, step, touchable):
#         self.step_count += 1
#
#     def EndSimulationAction(self):
#         self.end_time = time.time()
#         sec = g4_units.s
#         self.duration = (self.end_time - self.start_time) * sec
#
#     def write(self, filename):
#         sec = g4_units.s
#         f = open(filename, "w+")
#         s = f"# NumberOfRun    = {self.run_count}\n"
#         s += f"# NumberOfEvents = {self.event_count}\n"
#         s += f"# NumberOfTracks = {self.track_count}\n"
#         s += f"# NumberOfSteps  = {self.step_count}\n"
#         s += f"# NumberOfGeometricalSteps  = ?\n"
#         s += f"# NumberOfPhysicalSteps     = ?\n"
#         s += f"# ElapsedTime           = {self.duration / sec}\n"
#         s += f"# ElapsedTimeWoInit     = {self.duration / sec}\n"
#         s += f"# StartDate             = ?\n"
#         s += f"# EndDate               = ?\n"
#         s += f"# PPS (Primary per sec)      = {self.pps:.0f}\n"
#         s += f"# TPS (Track per sec)        = {self.tps:.0f}\n"
#         s += f"# SPS (Step per sec)         = {self.sps:.0f}\n"
#         if self.track_types_flag:
#             s += f"# Track types:\n"
#             for t in self.track_types:
#                 s += f"# {t} = {self.track_types[t]}\n"
#         f.write(s)


class KillActor(g4.GateKillActor, ActorBase):
    type_name = "KillActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateKillActor.__init__(self, user_info.__dict__)


"""
class ComptonSplittingActor(g4.GateComptonSplittingActor,ActorBase):
    type_name = "ComptonSplittingActor"
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.SplittingFactor = 0

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateComptonSplittingActor.__init__(self, user_info.__dict__)
"""


class ComptSplittingActor(g4.GateOptrComptSplittingActor, ActorBase):
    type_name = "ComptSplittingActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        deg = g4_units.deg
        user_info.splitting_factor = 1
        user_info.weight_threshold = 0
        user_info.bias_primary_only = True
        user_info.min_weight_of_particle = 0
        user_info.bias_only_once = True
        user_info.processes = ["compt"]
        user_info.russian_roulette = False
        user_info.rotation_vector_director = False
        user_info.vector_director = [0, 0, 1]
        user_info.max_theta = 90 * deg

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateOptrComptSplittingActor.__init__(self, user_info.__dict__)


class BremSplittingActor(g4.GateBOptrBremSplittingActor, ActorBase):
    type_name = "BremSplittingActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.splitting_factor = 1
        user_info.bias_primary_only = True
        user_info.bias_only_once = True
        user_info.processes = ["eBrem"]

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateBOptrBremSplittingActor.__init__(self, user_info.__dict__)
