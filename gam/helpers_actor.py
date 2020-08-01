from .SimulationStatisticsActor import *
from .DoseActor1 import *
from .DoseActor2 import *
from .DoseActor3 import *
from anytree import PreOrderIter

actor_builders = {'SimulationStatistics': lambda: SimulationStatisticsActor(),
                  'Dose1': lambda: DoseActor1(),
                  'Dose2': lambda: DoseActor2(),
                  'Dose3': lambda: DoseActor3()
                  }


def actor_build(actor_info):
    print('new actor ', actor_info)
    if actor_info.type not in actor_builders:
        s = f'Cannot find the actor {actor_info} in the list of actors types: \n' \
            f'Actor types {actor_builders}'

        gam.fatal(s)
    builder = actor_builders[actor_info.type]
    g4_actor = builder()
    return g4_actor


def actor_register_actions(simulation, actor_info):
    actions = actor_info.g4_actor.actions

    # Run
    ra = simulation.g4_UserActionInitialization.g4_RunAction
    ra.register_actor(actor_info)

    # Event
    ea = simulation.g4_UserActionInitialization.g4_EventAction
    ea.register_actor(actor_info)

    # Track
    ta = simulation.g4_UserActionInitialization.g4_TrackingAction
    ta.register_actor(actor_info)

    # Step: only enabled if attachTo a given volume.
    # Propagated to all child and sub-child
    tree = simulation.g4_UserDetectorConstruction.geometry_tree
    if 'attachedTo' not in actor_info:
        s = f'Error, actor must have an attachedTo attribute. Can be World by default. {actor_info}'
        gam.fatal(s)
    vol = actor_info.attachedTo
    if vol not in tree:
        s = f'Cannot attach the actor {actor_info.name} ' \
            f'because the volume {vol} does not exists'
        gam.fatal(s)
    for node in PreOrderIter(tree[vol]):
        print(f'Add actor {actor_info.name} to volume {node.name} (attached to {vol})')
        if 'ProcessHits' in actions:
            lv = simulation.g4_UserDetectorConstruction.g4_logical_volumes[node.name]
            actor_info.g4_actor.RegisterSD(lv)
    # initialization
    actor_info.g4_actor.BeforeStart()
