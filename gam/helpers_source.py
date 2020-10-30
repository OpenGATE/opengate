from .TestProtonPy2Source import *
from .TestProtonCppSource import *
from .TestProtonTimeSource import *
from .GenericSource import *
from .SourcePosition import *

source_type_names = {TestProtonPy2Source,
                     TestProtonTimeSource,
                     TestProtonCppSource,
                     GenericSource}
source_builders = gam.make_builders(source_type_names)

source_position_type_names = {SourcePositionBase,
                              SourcePositionDisc,
                              SourcePositionSphere}
source_position_builders = gam.make_builders(source_position_type_names)
