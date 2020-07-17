import gam
import gam_g4 as g4
from .SimulationStatisticsActor import *
from anytree import PreOrderIter

actor_builders = {'SimulationStatistics': lambda: SimulationStatisticsActor(),
                  # 'Dose': lambda: DoseActor()
                  }


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
    ea = simulation.g4_UserActionInitialization.g4_RunAction
    ea.register_actor(actor)
    # Event
    ea = simulation.g4_UserActionInitialization.g4_EventAction
    ea.register_actor(actor)
    # Track
    ea = simulation.g4_UserActionInitialization.g4_TrackingAction
    ea.register_actor(actor)
    # Batch
    # Step: propagate to all child and sub-child
    tree = simulation.g4_UserDetectorConstruction.geometry_tree
    if 'attachedTo' in actor:
        vol = actor.attachedTo
        if vol not in tree:
            s = f'Cannot attach the actor {actor.name} ' \
                f'because the volume {vol} does not exists'
            gam.fatal(s)
        for node in PreOrderIter(tree[vol]):
            print(f'Add actor {actor.name} to volume {node.name}')
            lv = simulation.g4_UserDetectorConstruction.g4_logical_volumes[node.name]
            actor.g4_actor.RegisterSD(lv)
    # initialization
    actor.g4_actor.BeforeStart()
