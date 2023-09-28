import uuid
from box import Box
from datetime import datetime
import uproot
import numpy as np
import time

import opengate_core as g4

from .base import ActorBase
from ..exception import fatal
from ..geometry.utility import rot_np_as_g4, vec_np_as_g4, vec_g4_as_np
from ..utility import g4_units
from ..userinfo import UserInfo


class SimulationStatisticsActor(g4.GateSimulationStatisticsActor, ActorBase):
    """
    Store statistics about a simulation run.
    """

    type_name = "SimulationStatisticsActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.track_types_flag = False
        user_info.output = ""

    def __init__(self, user_info=None):
        # need to initialize (sometimes it is read from disk)
        self.simulation = None
        # user_info can be null when create empty actor (that read file)
        if not user_info:
            user_info = UserInfo("Actor", self.type_name, name=uuid.uuid4().__str__())
        ActorBase.__init__(self, user_info)
        g4.GateSimulationStatisticsActor.__init__(self, user_info.__dict__)
        actions = {"EndSimulationAction"}
        self.AddActions(actions)
        # actions are also set from the cpp side
        # empty results for the moment
        self.counts = Box()
        self.counts.run_count = 0
        self.counts.event_count = 0
        self.counts.track_count = 0
        self.counts.step_count = 0
        self.counts.duration = 0
        self.counts.start_time = 0
        self.counts.stop_time = 0
        self.counts.init = 0
        self.counts.track_types = {}

    def __del__(self):
        # print("del SimulationStatisticsActor", self.user_info.name)
        pass

    @property
    def pps(self):
        sec = g4_units.s
        if self.counts.duration != 0:
            return self.counts.event_count / self.counts.duration * sec
        return 0

    @property
    def tps(self):
        sec = g4_units.s
        if self.counts.duration != 0:
            return self.counts.track_count / self.counts.duration * sec
        return 0

    @property
    def sps(self):
        sec = g4_units.s
        if self.counts.duration != 0:
            return self.counts.step_count / self.counts.duration * sec
        return 0

    @property
    def nb_thread(self):
        if self.simulation is not None:
            thread = self.simulation.user_info.number_of_threads
        else:
            thread = "?"
        return thread

    @property
    def simu_start_time(self):
        if not self.simulation is None:
            sim_start = self.simulation.run_timing_intervals[0][0]
        else:
            sim_start = 0
        return sim_start

    @property
    def simu_end_time(self):
        if not self.simulation is None:
            sim_end = self.simulation.run_timing_intervals[-1][1]
        else:
            sim_end = 0
        return sim_end

    def __str__(self):
        if not self.counts:
            return ""
        sec = g4_units.second
        s = (
            f"Runs      {self.counts.run_count}\n"
            f"Events    {self.counts.event_count}\n"
            f"Tracks    {self.counts.track_count}\n"
            f"Step      {self.counts.step_count}\n"
            f'Init      {self.counts.init / sec} \t{g4.G4BestUnit(self.counts.init, "Time")}\n'
            f'Duration  {self.counts.duration / sec} \t{g4.G4BestUnit(self.counts.duration, "Time")}\n'
            f"PPS       {self.pps:.0f}\n"
            f"TPS       {self.tps:.0f}\n"
            f"SPS       {self.sps:.0f}\n"
            f"start     {self.counts.start_time}\n"
            f"stop      {self.counts.stop_time}\n"
            f'Sim start {g4.G4BestUnit(self.simu_start_time, "Time")}\n'
            f'Sim end   {g4.G4BestUnit(self.simu_end_time, "Time")}\n'
            f"Threads   {self.nb_thread}"
        )
        if self.user_info.track_types_flag:
            s += f"\n" f"Track types: {self.counts.track_types}"
        return s

    def EndSimulationAction(self):
        g4.GateSimulationStatisticsActor.EndSimulationAction(self)
        self.counts = Box(self.GetCounts())
        # write the file if an output filename was set
        if self.user_info.output != "":
            self.write(self.user_info.output)

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

    def write(self, filename):
        """
        Attempt to be mostly compatible to previous Gate stat output file
        """
        sec = g4_units.s
        f = open(filename, "w+")
        s = f"# NumberOfRun    = {self.counts.run_count}\n"
        s += f"# NumberOfEvents = {self.counts.event_count}\n"
        s += f"# NumberOfTracks = {self.counts.track_count}\n"
        s += f"# NumberOfSteps  = {self.counts.step_count}\n"
        s += f"# NumberOfGeometricalSteps  = ?\n"
        s += f"# NumberOfPhysicalSteps     = ?\n"
        s += f"# ElapsedTime           = {self.counts.duration / sec + self.counts.init / sec}\n"
        s += f"# ElapsedTimeWoInit     = {self.counts.duration / sec}\n"
        s += (
            f'# StartDate             = {g4.G4BestUnit(self.simu_start_time, "Time")}\n'
        )
        s += f'# EndDate               = {g4.G4BestUnit(self.simu_end_time, "Time")}\n'
        s += f"# PPS (Primary per sec)      = {self.pps:.0f}\n"
        s += f"# TPS (Track per sec)        = {self.tps:.0f}\n"
        s += f"# SPS (Step per sec)         = {self.sps:.0f}\n"
        s += f"# Threads                    = {self.nb_thread}\n"
        s += f"# Date                       = {datetime.now()}\n"
        if self.user_info.track_types_flag:
            s += f"# Track types:\n"
            for t in self.counts.track_types:
                s += f"# {t} = {self.counts.track_types[t]}\n"
        f.write(s)


class MotionVolumeActor(g4.GateMotionVolumeActor, ActorBase):
    """
    Every run, move a volume according to the given translations and rotations.
    """

    type_name = "MotionVolumeActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.translations = []
        user_info.rotations = []
        user_info.priority = 10

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        # check rotations and translation
        u = user_info
        if len(u.translations) != len(u.rotations):
            fatal(
                f"Error, translations and rotations must have the same length, while it is"
                f" {len(u.translations)} and {len(u.rotations)}"
            )
        g4.GateMotionVolumeActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)
        self.g4_rotations = []
        self.g4_translations = []

    def __del__(self):
        pass

    def __str__(self):
        s = f"MotionVolumeActor {self.user_info.name}"
        return s

    def close(self):
        ActorBase.close(self)
        self.g4_rotations = []
        self.g4_translations = []

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)
        # check translations and rotations
        rt = self.simulation.run_timing_intervals
        ui = self.user_info
        if len(ui.translations) != len(rt):
            fatal(
                f"Error in actor {ui}. "
                f"Translations must be the same length than the number of runs. "
                f"While it is {len(ui.translations)} instead of {len(rt)}"
            )
        if len(ui.rotations) != len(rt):
            fatal(
                f"Error in actor {ui}. "
                f"Rotations must be the same length than the number of runs. "
                f"While it is {len(ui.rotations)} instead of {len(rt)}"
            )
        # convert rotation matrix and translation to g4
        for rot in ui.rotations:
            r = rot_np_as_g4(rot)
            self.g4_rotations.append(r)
        for tr in ui.translations:
            t = vec_np_as_g4(tr)
            self.g4_translations.append(t)
        # send rotations and translations to cpp
        self.SetTranslations(self.g4_translations)
        self.SetRotations(self.g4_rotations)


class SourceInfoActor(g4.GateVActor, ActorBase):
    """
    TODO
    """

    type_name = "SourceInfoActor"

    def __init__(self, name):
        g4.GateVActor.__init__(self, self.type_name)
        ActorBase.__init__(self, name)
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
            fatal(f"Provide a filename to the actor {self.user_info.physics_list_name}")
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
        self.positions.append(vec_g4_as_np(p))


class TestActor(g4.GateVActor, ActorBase):
    """
    Test actor: only py side (no cpp)
    For prototyping (slow)
    """

    type_name = "TestActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.track_types_flag = False

    def __init__(self, user_info=None):
        # user_info can be null when create empty actor (that read file)
        if not user_info:
            user_info = UserInfo("Actor", self.type_name, name=uuid.uuid4().__str__())
        ActorBase.__init__(self, user_info)
        g4.GateVActor.__init__(self, user_info.__dict__)
        actions = {
            "StartSimulationAction",
            "EndSimulationAction",
            "BeginOfEventAction",
            "EndOfRunAction",
            "PreUserTrackingAction",
            "SteppingAction",
        }
        self.AddActions(actions)
        # empty results for the moment
        self.run_count = 0
        self.event_count = 0
        self.track_count = 0
        self.step_count = 0
        self.duration = 0
        self.track_types = {}
        self.start_time = 0
        self.end_time = 0

    def __del__(self):
        pass

    @property
    def pps(self):
        sec = g4_units.s
        if self.duration != 0:
            return self.event_count / self.duration * sec
        return 0

    @property
    def tps(self):
        sec = g4_units.s
        if self.duration != 0:
            return self.track_count / self.duration * sec
        return 0

    @property
    def sps(self):
        sec = g4_units.s
        if self.duration != 0:
            return self.step_count / self.duration * sec
        return 0

    def __str__(self):
        if not self:
            return ""
        s = (
            f"Runs     {self.run_count}\n"
            f"Events   {self.event_count}\n"
            f"Tracks   {self.track_count}\n"
            f"Step     {self.step_count}\n"
            f'Duration {g4.G4BestUnit(self.duration, "Time")}\n'
            f"PPS      {self.pps:.0f}\n"
            f"TPS      {self.tps:.0f}\n"
            f"SPS      {self.sps:.0f}"
        )
        if self.user_info.track_types_flag:
            s += f"\n" f"Track types: {self.track_types}"
        return s

    def StartSimulationAction(self):
        self.start_time = time.time()

    def BeginOfEventAction(self, event):
        pass

    def PreUserTrackingAction(self, track):
        self.track_count += 1
        if self.user_info.track_types_flag:
            p = track.GetParticleName()
            try:
                self.track_types[p] += 1
            except:
                self.track_types[p] = 1

    def EndOfRunAction(self, run):
        self.run_count += 1
        self.event_count += run.GetNumberOfEvent()

    def SteppingAction(self, step, touchable):
        self.step_count += 1

    def EndSimulationAction(self):
        self.end_time = time.time()
        sec = g4_units.s
        self.duration = (self.end_time - self.start_time) * sec

    def write(self, filename):
        sec = g4_units.s
        f = open(filename, "w+")
        s = f"# NumberOfRun    = {self.run_count}\n"
        s += f"# NumberOfEvents = {self.event_count}\n"
        s += f"# NumberOfTracks = {self.track_count}\n"
        s += f"# NumberOfSteps  = {self.step_count}\n"
        s += f"# NumberOfGeometricalSteps  = ?\n"
        s += f"# NumberOfPhysicalSteps     = ?\n"
        s += f"# ElapsedTime           = {self.duration / sec}\n"
        s += f"# ElapsedTimeWoInit     = {self.duration / sec}\n"
        s += f"# StartDate             = ?\n"
        s += f"# EndDate               = ?\n"
        s += f"# PPS (Primary per sec)      = {self.pps:.0f}\n"
        s += f"# TPS (Track per sec)        = {self.tps:.0f}\n"
        s += f"# SPS (Step per sec)         = {self.sps:.0f}\n"
        if self.user_info.track_types_flag:
            s += f"# Track types:\n"
            for t in self.track_types:
                s += f"# {t} = {self.track_types[t]}\n"
        f.write(s)
