import json
import os
import random
import string

from box import Box

from opengate import g4_units
from opengate.actors.miscactors import SimulationStatisticsActor


def read_stat_file(filename, encoder=None):
    # for compatibility only, please use read_stats_file
    return read_stats_file(filename, encoder)


def read_stats_file(filename, encoder=None):
    if encoder == "json":
        return read_stats_file_json(filename)
    if encoder == "legacy":
        return read_stats_file_legacy(filename)
    # guess if it is json or not
    try:
        return read_stats_file_json(filename)
    except ValueError:
        pass
    return read_stats_file_legacy(filename)


def read_stats_file_json(filename):
    with open(filename, "r") as f:
        data = json.load(f)
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
    counts = {}
    for k, d in data.items():
        counts[k] = d["value"]
        u = d["unit"]
        if u in g4_units:
            counts[k] *= g4_units[u]
    stat = SimulationStatisticsActor(name=r)
    stat.user_output.stats.store_data("merged", counts)
    return stat


def read_stats_file_legacy(filename):
    p = os.path.abspath(filename)
    with open(p, "r") as f:
        lines = f.readlines()
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
    stats = SimulationStatisticsActor(name=r)
    counts = Box()
    read_track = False
    for line in lines:
        if "NumberOfRun" in line:
            counts.runs = int(line[len("# NumberOfRun    =") :])
        if "NumberOfEvents" in line:
            counts.events = int(line[len("# NumberOfEvents = ") :])
        if "NumberOfTracks" in line:
            counts.tracks = int(line[len("# NumberOfTracks =") :])
        if "NumberOfSteps" in line:
            counts.steps = int(line[len("# NumberOfSteps  =") :])
        sec = g4_units.s
        if "ElapsedTimeWoInit" in line:
            counts.duration = float(line[len("# ElapsedTimeWoInit     =") :]) * sec
        if read_track:
            w = line.split()
            name = w[1]
            value = w[3]
            counts.track_types[name] = value
        if "Track types:" in line:
            read_track = True
            stats.track_types_flag = True
            counts.track_types = {}
        if "StartDate" in line:
            counts.start_time = line[len("# StartDate             = ") :].replace(
                "\n", ""
            )
        if "EndDate" in line:
            counts.stop_time = line[len("# EndDate               = ") :].replace(
                "\n", ""
            )
        if "Threads" in line:
            a = line[len("# Threads                    =") :]
            try:
                counts.nb_threads = int(a)
            except:
                counts.nb_threads = "?"
    stats.user_output.stats.store_data("merged", counts)
    return stats


def sum_stats(stats1, stats2):
    stats = SimulationStatisticsActor(name="add")
    stats.import_user_output_from_actor(stats1, stats2)
    return stats


def write_stats(stats, filename):
    a = stats.user_output.stats.get_processed_output()
    with open(filename, "w") as f:
        json.dump(a, f, indent=4)
