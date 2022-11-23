from .ARFActor import *
from .ARFTrainingDatasetActor import *
from .DoseActor import *
from .DigitizerAdderActor import *
from .HitsReadoutActor import *
from .HitsEnergyWindowsActor import *
from .HitsProjectionActor import *
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
    HitsEnergyWindowsActor,
    HitsProjectionActor,
    HitsReadoutActor,
    MotionVolumeActor,
    ARFActor,
    ARFTrainingDatasetActor,
    TestActor,
}
actor_builders = gate.make_builders(actor_type_names)
