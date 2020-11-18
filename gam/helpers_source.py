from .GenericSource import *
from .Test1Source import *

"""
    --> added in helpers_element.py
    source_builders
    
        FIXME 
    source_position_builders
    source_direction_builders

"""

source_type_names = {GenericSource,
                     Test1Source}
source_builders = gam.make_builders(source_type_names)

