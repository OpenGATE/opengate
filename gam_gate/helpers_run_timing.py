import gam_gate as gam


def info_timing(i):
    s = f'[ {gam.g4_best_unit(i[0], "Time")}; {gam.g4_best_unit(i[1], "Time")}]'
    return s


def assert_run_timing(run_timing_intervals):
    if len(run_timing_intervals) < 0:
        gam.fatal(f'run_timing_interval must be an array '
                  f'with at least one element, while it is: {run_timing_intervals}')
    previous_end = run_timing_intervals[0][0]
    for i in run_timing_intervals:
        if len(i) != 2:
            gam.fatal(f'This run_timing_interval must have '
                      f'exactly one start and one end time, while it is: {i}')
        if i[0] > i[1]:
            gam.fatal(f'Start time must be lower or equal than end time: {i}')
        if i[0] < previous_end:
            gam.fatal(f'Start time must be larger or equal than previous end time: {i}, previous: {previous_end}')
        previous_end = i[1]


def info_run_timing(sim: gam.Simulation):
    rti = sim.run_timing_intervals
    s = f'Number of runs: {len(rti)}'
    nr = 0
    for i in rti:
        a = f'\nRun {nr}: {info_timing(i)}'
        s += gam.indent(2, a)
        nr += 1
    return s
