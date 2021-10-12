from .VoxelsSource import *
from .GenericSource import *

"""
    List of source types 
"""

source_type_names = {GenericSource, VoxelsSource}
source_builders = gam.make_builders(source_type_names)
