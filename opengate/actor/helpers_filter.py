import opengate as gate
from .ParticleFilter import ParticleFilter
from .KineticEnergyFilter import KineticEnergyFilter
from .TrackCreatorProcessFilter import TrackCreatorProcessFilter

filter_type_names = {ParticleFilter, KineticEnergyFilter, TrackCreatorProcessFilter}
filter_builders = gate.make_builders(filter_type_names)
