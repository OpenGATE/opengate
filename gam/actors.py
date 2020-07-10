import gam
import gam_g4 as g4
from .SimulationStatisticsActor import *
from anytree import PreOrderIter

actor_builders = {'SimulationStatistics': lambda: SimulationStatisticsActor(),
                  # 'Dose': lambda: DoseActor()
                  }


# self.listeners = ['BeginOfRunAction',
#                          'BeginOfEventAction',
#                          'BeginOfTrackAction',
#                          'ProcessHits']

def actor_build(actor):
    print('new actor ', actor)
    if actor.type not in actor_builders:
        s = f'Cannot find the actor {actor} in the list of actors types: \n' \
            f'Actor types {actor_builders}'

        gam.fatal(s)
    builder = actor_builders[actor.type]
    g4_actor = builder()
    return g4_actor


def actor_register_actions(simulation, actor):
    actions = actor.g4_actor.actions
    # Run
    ea = simulation.g4_action.g4_run_action
    ea.register_actor(actor)
    # Event
    ea = simulation.g4_action.g4_event_action
    ea.register_actor(actor)
    # Track
    ea = simulation.g4_action.g4_tracking_action
    ea.register_actor(actor)
    # Batch
    # Step: propagate to all child and sub-child
    if 'attachedTo' in actor:
        vol = actor.attachedTo
        for node in PreOrderIter(simulation.g4_geometry.geometry_tree[vol]):
            print(f'Add actor {actor.name} to volume {node.name}')
            lv = simulation.g4_geometry.g4_logical_volumes[node.name]
            actor.g4_actor.RegisterSD(lv)
        actor.g4_actor.batch_size = 10000
    # initialization
    actor.g4_actor.BeforeStart()
