from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor,
                    SourceInfoActor}
actor_builders = gam.make_builders(actor_type_names)
