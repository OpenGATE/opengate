from .filters import KineticEnergyFilter, ParticleFilter, TrackCreatorProcessFilter
from ..utility import make_builders

filter_type_names = {ParticleFilter, KineticEnergyFilter, TrackCreatorProcessFilter}
filter_builders = make_builders(filter_type_names)
