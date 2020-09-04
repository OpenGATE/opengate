import gam
from .TestProtonPySource import *
from .TestProtonPy2Source import *
from .TestProtonCppSource import *
from .TestProtonTimeSource import *

source_builders = {
    'TestProtonPy': lambda x: TestProtonPySource(x),
    'TestProtonPy2': lambda x: TestProtonPy2Source(x),
    'TestProtonTime': lambda x: TestProtonTimeSource(x),
    'TestProtonCpp': lambda x: TestProtonCppSource(x),
}


def source_build(source_info):
    if source_info.type not in source_builders:
        s = f'Cannot find the source {source_info} in the list of sources types: \n' \
            f'source types {source_builders}'

        gam.fatal(s)
    builder = source_builders[source_info.type]
    g4_source = builder(source_info)
    return g4_source


def get_estimated_total_number_of_events(sim: gam.Simulation):
    run_timing_intervals = sim.run_timing_intervals
    sources_info = sim.sources_info
    sec = gam.g4_units('second')
    total = 0
    run = 0
    for time_interval in run_timing_intervals:
        print('run ', run, ' time', time_interval[0] / sec, time_interval[1] / sec)
        for source_info in sources_info.values():
            n = source_info.g4_source.get_estimated_number_of_events(time_interval)
            print(f'Source {source_info.name} : {n} events')
            total += n
        run += 1
    return round(total)
