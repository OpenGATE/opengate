from .ARFActor import *
from .ARFTrainingDatasetActor import *
from .DoseActor import *
from .DigitizerAdderActor import *
from .DigitizerReadoutActor import *
from .DigitizerEnergyWindowsActor import *
from .DigitizerProjectionActor import *
from .DigitizerGaussianBlurringActor import *
from .MotionVolumeActor import *
from .PhaseSpaceActor import *
from .SimulationStatisticsActor import *
from .SourceInfoActor import *
from .TestActor import *

actor_type_names = {
    SimulationStatisticsActor,
    DoseActor,
    SourceInfoActor,
    PhaseSpaceActor,
    DigitizerHitsCollectionActor,
    DigitizerAdderActor,
    DigitizerEnergyWindowsActor,
    DigitizerProjectionActor,
    DigitizerReadoutActor,
    DigitizerGaussianBlurringActor,
    MotionVolumeActor,
    ARFActor,
    ARFTrainingDatasetActor,
    TestActor,
}
actor_builders = gate.make_builders(actor_type_names)
