from .TestProtonPy2Source import *
from .TestProtonCppSource import *
from .TestProtonTimeSource import *
from .GenericSource import *
from .SourcePosition import *
from .SourceDirection import *
from .SingleParticleSource import *
from .Test1Source import *

"""
    --> added in helpers_element.py
    source_builders
    
        FIXME 
    source_position_builders
    source_direction_builders

"""

source_type_names = {TestProtonPy2Source,
                     TestProtonTimeSource,
                     TestProtonCppSource,
                     SingleParticleSource,
                     GenericSource,
                     Test1Source}
source_builders = gam.make_builders(source_type_names)

source_position_type_names = {SourcePositionBase,
                              SourcePositionDisc,
                              SourcePositionPoint,
                              SourcePositionSphere}
source_position_builders = gam.make_builders(source_position_type_names)

source_direction_type_names = {SourceDirectionBase}
source_direction_builders = gam.make_builders(source_direction_type_names)
