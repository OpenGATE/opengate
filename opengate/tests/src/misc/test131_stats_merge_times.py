#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Merge of the statistics (SimulationStatisticsActor), e.g. of several jobs:
- start_time / stop_time are the earliest start and the latest stop, compared
  as dates (they were compared as strings, and only the last merged item was
  kept when merging one at a time);
- sim_start_time / sim_stop_time cover all the merged items;
- duration is summed (total computing time), timespan is the wall-clock time
  from the first start to the last stop;
- jobs is the number of merged simulations, whatever the merge order;
- threads is the number of threads of the jobs (was 1 after a merge);
- pps is the speed of one job, pps_timespan the speed of all the jobs;
- the statistics of each run contain the simulated time of the run.
"""

import opengate as gate
from opengate.actors.dataitems import StatisticsDataItem, parse_ctime
from opengate.tests import utility

sec = gate.g4_units.s
hour = 3600 * sec


def make_stats(
    start_time, stop_time, sim_start, sim_stop, duration, events, simulation_id
):
    item = StatisticsDataItem()
    item.set_data(
        {
            "runs": 1,
            "events": events,
            "duration": duration,
            "start_time": start_time,
            "stop_time": stop_time,
            "sim_start_time": sim_start,
            "sim_stop_time": sim_stop,
            "simulation_ids": [simulation_id],
            "nb_threads": 4,
        }
    )
    return item


def check_merged(merged, name):
    print(f"--- {name}")
    print(merged)
    is_ok = True
    for key, value, ref in [
        ("runs", merged.runs, 3),
        ("events", merged.events, 600_000_000),
        ("duration", merged.duration, 9 * hour),
        # earliest start and latest stop: across days, "Sun" < "Sat" as strings
        ("start_time", merged.start_time, "Sat Oct 24 21:00:00 2026"),
        ("stop_time", merged.stop_time, "Sun Oct 25 02:00:00 2026"),
        ("timespan", merged.timespan, 5 * hour),
        ("sim_start_time", merged.sim_start_time, 0 * sec),
        ("sim_stop_time", merged.sim_stop_time, 30 * sec),
        ("jobs", merged.jobs, 3),
        ("threads", merged.nb_threads, 4),
        # 600 M events in 9 h of computing (3 jobs), in 5 h of wall-clock time
        ("pps", merged.pps, 18518),
        ("pps_timespan", merged.pps_timespan, 33333),
    ]:
        b = value == ref
        utility.print_test(b, f"{name}: {key} = {value} (expected {ref})")
        is_ok = is_ok and b
    return is_ok


def test_merge_of_data_items():
    # three jobs run in parallel (3 h each), the last one stopping after midnight
    jobs = [
        make_stats(
            "Sat Oct 24 21:00:00 2026",
            "Sun Oct 25 00:00:00 2026",
            0,
            10 * sec,
            3 * hour,
            100_000_000,
            "job1",
        ),
        make_stats(
            "Sat Oct 24 23:00:00 2026",
            "Sun Oct 25 02:00:00 2026",
            20 * sec,
            30 * sec,
            3 * hour,
            300_000_000,
            "job2",
        ),
        make_stats(
            "Sat Oct 24 22:00:00 2026",
            "Sun Oct 25 01:00:00 2026",
            10 * sec,
            20 * sec,
            3 * hour,
            200_000_000,
            "job3",
        ),
    ]

    # merged one at a time (as when merging the outputs of jobs)
    merged = StatisticsDataItem()
    for job in jobs:
        merged.inplace_merge_with(job)
    is_ok = check_merged(merged, "one at a time")

    # merged all at once, starting from the second job
    merged = jobs[1].merge_with(jobs[0])
    merged.inplace_merge_with(jobs[2])
    is_ok = check_merged(merged, "starting from a job") and is_ok

    # two runs of the same job, then another job: 2 jobs
    merged = StatisticsDataItem()
    merged.inplace_merge_with(jobs[0])
    merged.inplace_merge_with(jobs[0].merge_with(jobs[0]))
    b = merged.jobs == 1
    merged.inplace_merge_with(jobs[1])
    b = b and merged.jobs == 2 and len(jobs[0].simulation_ids) == 1
    utility.print_test(b, f"runs of the same job: jobs = {merged.jobs} (expected 2)")
    is_ok = is_ok and b

    # ctime pads the day with a space; unset times are not dates
    b = parse_ctime("Sun Oct  4 01:02:03 2026") is not None
    b = b and parse_ctime(0) is None and parse_ctime("") is None
    utility.print_test(b, "parse_ctime (padded day, unset time)")
    return is_ok and b


def test_simulated_time_of_runs():
    sim = gate.Simulation()
    sim.number_of_threads = 1
    sim.run_timing_intervals = [[0, 1 * sec], [1 * sec, 3 * sec], [5 * sec, 6 * sec]]
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 100 * gate.g4_units.keV
    source.number_of_primaries = [50, 50, 50]
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.stats.keep_data_per_run = True
    stats.stats.write_to_disk = False
    sim.run(start_new_process=False)

    print("--- runs")
    is_ok = True
    for i, (start, stop) in enumerate(sim.run_timing_intervals):
        run = stats.stats.get_data(which=i)
        b = run.sim_start_time == start and run.sim_stop_time == stop
        utility.print_test(
            b,
            f"run {i}: sim_start_time = {run.sim_start_time / sec} s, "
            f"sim_stop_time = {run.sim_stop_time / sec} s",
        )
        is_ok = is_ok and b

    # merging the runs gives the simulated time of all of them
    merged = StatisticsDataItem()
    for i in range(len(sim.run_timing_intervals)):
        run = StatisticsDataItem()
        run.set_data(stats.stats.get_data(which=i))
        merged.inplace_merge_with(run)
    b = merged.sim_start_time == 0 and merged.sim_stop_time == 6 * sec
    b = b and merged.events == 150 and merged.timespan >= 0 and merged.jobs == 1
    utility.print_test(b, f"merged runs: from 0 to {merged.sim_stop_time / sec} s")
    return is_ok and b


if __name__ == "__main__":
    is_ok = test_merge_of_data_items()
    is_ok = test_simulated_time_of_runs() and is_ok
    utility.test_ok(is_ok)
