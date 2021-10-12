import gam_gate as gam
from .ParticleFilter import ParticleFilter

filter_type_names = {ParticleFilter}
filter_builders = gam.make_builders(filter_type_names)
