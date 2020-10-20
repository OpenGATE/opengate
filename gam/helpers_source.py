from .TestProtonPy2Source import *
from .TestProtonCppSource import *
from .TestProtonTimeSource import *

source_builders = {
    TestProtonPy2Source.source_type: lambda x: TestProtonPy2Source(x),
    TestProtonTimeSource.source_type: lambda x: TestProtonTimeSource(x),
    TestProtonCppSource.source_type: lambda x: TestProtonCppSource(x),
}


def get_source_builder(source_type):
    if source_type not in source_builders:
        s = f'Cannot find the source {source_type} in the list of sources types: \n' \
            f'source types {source_builders.keys()}'

        gam.fatal(s)
    builder = source_builders[source_type]
    return builder
