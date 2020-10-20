from .SimulationStatisticsActor import *
from .DoseActor1 import *
from .DoseActor2 import *
from .DoseActor import *
from gam import log

actor_builders = {
    SimulationStatisticsActor.actor_type: lambda x: SimulationStatisticsActor(x),
    DoseActor.actor_type: lambda x: DoseActor(x)
}


def get_actor_builder(actor_type):
    if actor_type not in gam.actor_builders:
        s = f'Cannot find the actor type {actor_type} in the list of actors types: \n' \
            f'Actor types {actor_builders.keys()}'
        gam.fatal(s)
    return actor_builders[actor_type]


