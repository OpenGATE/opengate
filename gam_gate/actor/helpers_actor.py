from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *
from .PhaseSpaceActor import *
from .TestActor import *
from .HitsCollectionActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor,
                    SourceInfoActor,
                    PhaseSpaceActor,
                    HitsCollectionActor,
                    TestActor}
actor_builders = gam_gate.make_builders(actor_type_names)
