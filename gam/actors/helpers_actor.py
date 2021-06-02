from .SimulationStatisticsActor import *
from .DoseActor import *
from .SourceInfoActor import *
from .PhaseSpaceActor import *

actor_type_names = {SimulationStatisticsActor,
                    DoseActor,
                    SourceInfoActor,
                    PhaseSpaceActor}
actor_builders = gam.make_builders(actor_type_names)
