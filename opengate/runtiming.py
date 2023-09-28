from .utility import g4_best_unit, indent
from .exception import fatal


def info_timing(i):
    s = f'[ {g4_best_unit(i[0], "Time")}; {g4_best_unit(i[1], "Time")}]'
    return s


def assert_run_timing(run_timing_intervals):
    if len(run_timing_intervals) < 0:
        fatal(
            f"run_timing_interval must be an array "
            f"with at least one element, while it is: {run_timing_intervals}"
        )
    previous_end = run_timing_intervals[0][0]
    for i in run_timing_intervals:
        if len(i) != 2:
            fatal(
                f"This run_timing_interval must have "
                f"exactly one start and one end time, while it is: {i}"
            )
        if i[0] > i[1]:
            fatal(f"Start time must be lower or equal than end time: {i}")
        if i[0] < previous_end:
            fatal(
                f"Start time must be larger or equal than previous end time: {i}, previous: {previous_end}"
            )
        previous_end = i[1]


def info_run_timing(sim):
    rti = sim.run_timing_intervals
    s = f"Number of runs: {len(rti)}"
    nr = 0
    for i in rti:
        a = f"\nRun {nr}: {info_timing(i)}"
        s += indent(2, a)
        nr += 1
    return s


def range_timing(start, end, n):
    """
    Return a list of n time intervals, from start to end
    e.g. range_timing(0, 1, 10)
    => [0, 0.1], [0.1, 0.2], [0.2, 0.3], [0.3, 0.4], [0.4, 0.5],
    [0.5, 0.6], [0.6, 0.7], [0.7, 0.8], [0.8, 0.9], [0.9, 1.0]]
    """
    t = []
    duration = end - start
    step = duration / n
    for i in range(n):
        interval = [start, start + step]
        t.append(interval)
        start = start + step
    return t
