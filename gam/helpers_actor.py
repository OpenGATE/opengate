from .SimulationStatisticsActor import *
from .DoseActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor}
actor_builders = gam.make_builders(actor_type_names)
