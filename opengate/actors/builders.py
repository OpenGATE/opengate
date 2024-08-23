from .filters import (
    KineticEnergyFilter,
    ParticleFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
    ScatterFilter,
)
from ..utility import make_builders

filter_type_names = {
    ParticleFilter,
    KineticEnergyFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
    ScatterFilter,
}
filter_builders = make_builders(filter_type_names)
