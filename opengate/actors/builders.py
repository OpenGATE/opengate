from .filters import (
    KineticEnergyFilter,
    ParticleFilter,
    TrackCreatorProcessFilter,
    ValueAttributeFilter,
)
from ..utility import make_builders

filter_type_names = {
    ParticleFilter,
    KineticEnergyFilter,
    TrackCreatorProcessFilter,
    ValueAttributeFilter,
}
filter_builders = make_builders(filter_type_names)
