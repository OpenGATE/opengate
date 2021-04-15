from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *
from .HitsActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor,
                    SourceInfoActor,
                    HitsActor}
actor_builders = gam.make_builders(actor_type_names)
