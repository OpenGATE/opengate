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
from .miscactors import (
    MotionVolumeActor,
    SimulationStatisticsActor,
    SourceInfoActor,
    TestActor,
    KillActor,
    BremSplittingActor,
    ComptSplittingActor,
    ComptPseudoTransportationActor,
)
from ..utility import make_builders


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
    KillActor,
    BremSplittingActor,
    ComptSplittingActor,
    ComptPseudoTransportationActor,
}
actor_builders = make_builders(actor_type_names)
