from .ParticleFilter import ParticleFilter
from .KineticEnergyFilter import KineticEnergyFilter
from .TrackCreatorProcessFilter import TrackCreatorProcessFilter
from ..helpers import make_builders

filter_type_names = {ParticleFilter, KineticEnergyFilter, TrackCreatorProcessFilter}
filter_builders = make_builders(filter_type_names)
