import gam_gate as gam
from .ParticleFilter import ParticleFilter
from .KineticEnergyFilter import KineticEnergyFilter

filter_type_names = {ParticleFilter, KineticEnergyFilter}
filter_builders = gam.make_builders(filter_type_names)
