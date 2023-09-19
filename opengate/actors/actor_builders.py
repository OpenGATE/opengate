from .arfactors import ARFActor
from .arfactors import ARFTrainingDatasetActor
from .DoseActor import DoseActor
from .LETActor import LETActor
from .DigitizerAdderActor import DigitizerAdderActor
from .DigitizerReadoutActor import DigitizerReadoutActor
from .DigitizerHitsCollectionActor import DigitizerHitsCollectionActor
from .DigitizerEnergyWindowsActor import DigitizerEnergyWindowsActor
from .DigitizerProjectionActor import DigitizerProjectionActor
from .DigitizerBlurringActor import DigitizerBlurringActor
from .DigitizerSpatialBlurringActor import DigitizerSpatialBlurringActor
from .DigitizerEfficiencyActor import DigitizerEfficiencyActor
from .MotionVolumeActor import MotionVolumeActor
from .PhaseSpaceActor import PhaseSpaceActor
from .SimulationStatisticsActor import SimulationStatisticsActor
from .SourceInfoActor import SourceInfoActor
from .TestActor import TestActor
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
