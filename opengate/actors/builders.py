from .filters import (
    KineticEnergyFilter,
    ParticleFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
)
from ..utility import make_builders

filter_type_names = {
    ParticleFilter,
    KineticEnergyFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
}
filter_builders = make_builders(filter_type_names)
