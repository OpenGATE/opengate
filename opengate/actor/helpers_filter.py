import opengate as gate
from .ParticleFilter import ParticleFilter
from .KineticEnergyFilter import KineticEnergyFilter

filter_type_names = {ParticleFilter, KineticEnergyFilter}
filter_builders = gate.make_builders(filter_type_names)
