import gam
import gam_g4 as g4
from .TestProtonPySource import *
from .TestProtonCppSource import *

source_builders = {
    'TestProtonPy': lambda x: TestProtonPySource(x),
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
