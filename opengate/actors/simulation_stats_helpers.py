import random
from opengate.actors.miscactors import SimulationStatisticsActor
import string
import json
from box import Box
from opengate import g4_units
import os


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
    stat.user_output.stats.store_data(counts)
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
    stats.user_output.stats.store_data(counts)
    return stats


def sum_stats(stats1, stats2):
    stats = SimulationStatisticsActor(name="add")
    k_int = {"runs", "events", "tracks", "steps"}
    k_float = {"duration", "sim_start_time", "sim_stop_time"}
    k_date = {"start_time", "stop_time"}
    k_str = {"arch", "python"}

    counts = stats1.counts.copy()
    for k, v1 in stats1.counts.items():
        v2 = stats2.counts[k]
        if k not in stats1.counts:
            continue
        v1 = stats1.counts[k]
        if k in k_int:
            counts[k] = int(v1) + int(v2)
        if k in k_float:
            counts[k] = float(v1) + float(v2)
        if k in k_date:
            counts[k] = str(v1).replace("\n", "") + " _ " + str(v2).replace("\n", "")
        if k in k_str:
            if v1 != v2:
                counts[k] = str(v1) + " " + str(v2)
            else:
                counts[k] = v1
        if k == "track_types":
            v = v1.copy()
            for kk, vv in v1.items():
                if kk in v2:
                    v[kk] = int(v1[kk]) + int(v2[kk])
            for kk, vv in v2.items():
                if kk not in v1:
                    v[kk] = int(v2[kk])
            counts[k] = v

    stats.user_output.stats.store_data(counts)
    return stats


def write_stats(stats, filename):
    a = stats.user_output.stats.get_processed_output()
    with open(filename, "w") as f:
        json.dump(a, f, indent=4)
