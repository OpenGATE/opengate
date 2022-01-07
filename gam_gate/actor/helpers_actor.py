from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *
from .PhaseSpaceActor2 import *
from .TestActor import *
from .HitsCollectionActor import *
from .HitsAdderActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor,
                    SourceInfoActor,
                    PhaseSpaceActor2,
                    HitsCollectionActor,
                    HitsAdderActor,
                    TestActor}
actor_builders = gam.make_builders(actor_type_names)
