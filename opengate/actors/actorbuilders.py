from .arfactors import ARFActor, ARFTrainingDatasetActor
from .doseactors import DoseActor, LETActor, FluenceActor
from .chemistryactors import ChemistryActor, ChemistryLongTimeActor
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
)
from .dynamicactors import DynamicGeometryActor
from ..utility import make_builders


actor_type_names = {
    SimulationStatisticsActor,
    DoseActor,
    FluenceActor,
    LETActor,
    ChemistryActor,
    ChemistryLongTimeActor,
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
    DynamicGeometryActor,
}
actor_builders = make_builders(actor_type_names)
