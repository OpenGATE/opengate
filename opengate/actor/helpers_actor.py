from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *
from .PhaseSpaceActor import *
from .TestActor import *
from .HitsCollectionActor import *
from .HitsAdderActor import *
from .HitsEnergyWindowsActor import *
from .HitsProjectionActor import *
from .MotionVolumeActor import *
from .ARFActor import *
from .ARFTrainingDatasetActor import *

actor_type_names = {
    SimulationStatisticsActor,
    DoseActor,
    SourceInfoActor,
    PhaseSpaceActor,
    HitsCollectionActor,
    HitsAdderActor,
    HitsEnergyWindowsActor,
    HitsProjectionActor,
    MotionVolumeActor,
    ARFActor,
    ARFTrainingDatasetActor,
    TestActor,
}
actor_builders = gate.make_builders(actor_type_names)
