from .filters import (
    KineticEnergyFilter,
    ParticleFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
    UnscatteredPrimaryFilter,
)
from ..utility import make_builders

filter_type_names = {
    ParticleFilter,
    KineticEnergyFilter,
    TrackCreatorProcessFilter,
    ThresholdAttributeFilter,
    UnscatteredPrimaryFilter,
}
filter_builders = make_builders(filter_type_names)
