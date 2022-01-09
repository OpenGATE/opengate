from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *
from .PhaseSpaceActor import *
from .TestActor import *
from .HitsCollectionActor import *
from .HitsAdderActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor,
                    SourceInfoActor,
                    PhaseSpaceActor,
                    HitsCollectionActor,
                    HitsAdderActor,
                    TestActor}
actor_builders = gam.make_builders(actor_type_names)
