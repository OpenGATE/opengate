from .filters import (
    KineticEnergyFilter,
    ParticleFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
    PrimaryScatterFilter,
)
from ..utility import make_builders

filter_type_names = {
    ParticleFilter,
    KineticEnergyFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
    PrimaryScatterFilter,
}
filter_builders = make_builders(filter_type_names)
