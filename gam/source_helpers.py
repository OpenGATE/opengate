import gam
import gam_g4 as g4
import sys
import numpy as np
from .TestProtonPySource import *
from .TestProtonPy2Source import *
from .TestProtonCppSource import *

source_builders = {
    'TestProtonPy': lambda x: TestProtonPySource(x),
    'TestProtonPy2': lambda x: TestProtonPy2Source(x),
    'TestProtonCpp': lambda x: TestProtonCppSource(x),
}


def source_build(source):
    if source.type not in source_builders:
        s = f'Cannot find the source {source} in the list of sources types: \n' \
            f'source types {source_builders}'

        gam.fatal(s)
    builder = source_builders[source.type]
    g4_source = builder(source)
    return g4_source


def all_sources_are_terminated(t, sources):
    for s in sources:
        if not s.is_terminated(t):  # will check time and/or total number of simulated particles
            return False
    return True


def get_next_source_event_info(current_time, sources):
    """
    Return the next source and its associated time.
    Consider the current time (t) and loop over all the sources. Select the one with the lowest time, or,
    in case of equality the one with the lowest event id.
    """
    next_time = sys.float_info.max
    next_event_id = sys.float_info.max
    next_source = sources[0]
    for s in sources:
        source_time, event_id = s.get_next_event_info(current_time)
        if source_time < next_time or (source_time == next_time and event_id < next_event_id):
            next_time = source_time
            next_source = s
            next_event_id = event_id
    return next_time, next_source
