from .SimulationStatisticsActor import *
from .SimulationStatisticsActor2 import *
from .DoseActor import *
from .SourceInfoActor import *

actor_type_names = {SimulationStatisticsActor,
                    SimulationStatisticsActor2,
                    DoseActor,
                    SourceInfoActor}
actor_builders = gam.make_builders(actor_type_names)
