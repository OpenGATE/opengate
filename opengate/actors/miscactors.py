from box import Box
import platform
import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units, g4_best_unit_tuple
from .actoroutput import ActorOutputBase
from ..serialization import dump_json


class ActorOutputStatisticsActor(ActorOutputBase):
    """This is a hand-crafted ActorOutput specifically for the SimulationStatisticsActor."""

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

        self.default_suffix = "json"

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
        self.merged_data.nb_threads = 1

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
        d["runs"] = {"value": self.merged_data.run_count, "unit": None}
        d["events"] = {"value": self.merged_data.event_count, "unit": None}
        d["tracks"] = {"value": self.merged_data.track_count, "unit": None}
        d["steps"] = {"value": self.merged_data.step_count, "unit": None}
        val, unit = g4_best_unit_tuple(self.merged_data.init, "Time")
        d["init"] = {
            "value": val,
            "unit": unit,
        }
        val, unit = g4_best_unit_tuple(self.merged_data.duration, "Time")
        d["duration"] = {
            "value": val,
            "unit": unit,
        }
        val, unit = g4_best_unit_tuple(self.pps, "Time")
        d["pps"] = {"value": val, "unit": unit}
        val, unit = g4_best_unit_tuple(self.tps, "Time")
        d["tps"] = {"value": val, "unit": unit}
        val, unit = g4_best_unit_tuple(self.sps, "Time")
        d["sps"] = {"value": val, "unit": unit}
        d["start_time"] = {
            "value": self.merged_data.start_time,
            "unit": None,
        }
        d["stop_time"] = {
            "value": self.merged_data.stop_time,
            "unit": None,
        }
        val, unit = g4_best_unit_tuple(self.merged_data.sim_start_time, "Time")
        d["sim_start_time"] = {
            "value": val,
            "unit": unit,
        }
        val, unit = g4_best_unit_tuple(self.merged_data.sim_stop_time, "Time")
        d["sim_stop_time"] = {
            "value": val,
            "unit": unit,
        }
        d["threads"] = {"value": self.merged_data.nb_threads, "unit": None}
        d["arch"] = {"value": platform.system(), "unit": None}
        d["python"] = {"value": platform.python_version(), "unit": None}
        d["track_types"] = {"value": self.merged_data.track_types, "unit": None}
        return d

    def __str__(self):
        s = ""
        for k, v in self.get_processed_output().items():
            if k == "track_types":
                if len(v["value"]) > 0:
                    s += "track_types\n"
                    for t, n in v["value"].items():
                        s += f"{' ' * 24}{t}: {n}\n"
            else:
                if v["unit"] is None:
                    unit = ""
                else:
                    unit = str(v["unit"])
                s += f"{k}{' ' * (20 - len(k))}{v['value']} {unit}\n"
        return s

    def write_data(self):
        """Override virtual method from base class."""
        with open(self.get_output_path("merged"), "w+") as f:
            if self.encoder == "json":
                dump_json(self.get_processed_output(), f, indent=4)
            else:
                f.write(self.__str__())


class SimulationStatisticsActor(ActorBase, g4.GateSimulationStatisticsActor):
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
        self._add_user_output(ActorOutputStatisticsActor, "stats")
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateSimulationStatisticsActor.__init__(self, {"name": self.name})
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def __str__(self):
        s = ActorBase.__str__(self)
        s += "\n"
        s += "User output:\n"
        s += self.user_output["stats"].__str__()
        return s

    @property
    def counts(self):
        return self.user_output.stats.merged_data

    def store_output_data(self, output_name, run_index, *data):
        raise NotImplementedError

    def initialize(self):
        ActorBase.initialize(self)

        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

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

    # def set_default_user_info(user_info):
    #     ActorBase.set_default_user_info(user_info)

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        g4.GateKillActor.__init__(self, self.user_info)


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
