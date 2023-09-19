from .arfactors import ARFActor, ARFTrainingDatasetActor
from .doseactors import DoseActor, LETActor
from .digitizers import (
    DigitizerAdderActor,
    DigitizerReadoutActor,
    DigitizerHitsCollectionActor,
    DigitizerEnergyWindowsActor,
    DigitizerProjectionActor,
    DigitizerBlurringActor,
    DigitizerSpatialBlurringActor,
    DigitizerEfficiencyActor,
    PhaseSpaceActor,
)
from .misc import (
    MotionVolumeActor,
    SimulationStatisticsActor,
    SourceInfoActor,
    TestActor,
)
from ..helpers import make_builders


actor_type_names = {
    SimulationStatisticsActor,
    DoseActor,
    LETActor,
    SourceInfoActor,
    PhaseSpaceActor,
    DigitizerHitsCollectionActor,
    DigitizerAdderActor,
    DigitizerEnergyWindowsActor,
    DigitizerProjectionActor,
    DigitizerReadoutActor,
    DigitizerBlurringActor,
    DigitizerSpatialBlurringActor,
    DigitizerEfficiencyActor,
    MotionVolumeActor,
    ARFActor,
    ARFTrainingDatasetActor,
    TestActor,
}
actor_builders = make_builders(actor_type_names)
