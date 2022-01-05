from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *
from .PhaseSpaceActor2 import *
from .TestActor import *
from .HitsCollectionActor import *
from .SinglesCollectionActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor,
                    SourceInfoActor,
                    PhaseSpaceActor2,
                    HitsCollectionActor,
                    SinglesCollectionActor,
                    TestActor}
actor_builders = gam.make_builders(actor_type_names)
