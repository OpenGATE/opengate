from .SimulationStatisticsActor import *
from .DoseActor1 import *
from .DoseActor2 import *
from .DoseActor import *
from gam import log

actor_builders = {'SimulationStatisticsActor': lambda x, y: SimulationStatisticsActor(x, y),
                  'Dose1': lambda x, y: DoseActor1(x, y),
                  'Dose2': lambda x, y: DoseActor2(x, y),
                  'DoseActor': lambda x, y: DoseActor(x, y)
                  }


# FIXME LATER --> need A ActorBase(user_info)

def actor_build(simu, actor_info):
    if actor_info.type not in actor_builders:
        s = f'Cannot find the actor {actor_info} in the list of actors types: \n' \
            f'Actor types {actor_builders}'
        gam.fatal(s)
    builder = actor_builders[actor_info.type]
    g4_actor = builder(simu, actor_info)
    return g4_actor


def actor_register_actions(simulation, actor_info):
    actions = actor_info.g4_actor.actions

    # Run
    ra = simulation.action_manager.g4_RunAction
    ra.register_actor(actor_info)

    # Event
    ea = simulation.action_manager.g4_EventAction
    ea.register_actor(actor_info)

    # Track
    ta = simulation.action_manager.g4_TrackingAction
    ta.register_actor(actor_info)

    # Step: only enabled if attachTo a given volume.
    # Propagated to all child and sub-child
    tree = simulation.volume_manager.volumes_tree
    if 'attachedTo' not in actor_info:
        s = f'Error, actor must have an "attachedTo" attribute. ' \
            f'It can be World by default. Current info: \n{actor_info}'
        gam.fatal(s)
    vol = actor_info.attachedTo
    if vol not in tree:
        s = f'Cannot attach the actor {actor_info.name} ' \
            f'because the volume {vol} does not exists'
        gam.fatal(s)

    # Propagate the Geant4 Sensitive Detector to all childs
    lv = simulation.volume_manager.volumes[vol].g4_logical_volume
    register_sensitive_detector_to_childs(actor_info.g4_actor, lv)

    # initialization
    actor_info.g4_actor.BeforeStart()


def register_sensitive_detector_to_childs(actor, lv):
    log.debug(f'Add actor "{actor.user_info.name}" '
              f'(attached to "{actor.user_info.attachedTo}") '
              f'to volume "{lv.GetName()}"')
    actor.RegisterSD(lv)
    n = lv.GetNoDaughters()
    for i in range(n):
        child = lv.GetDaughter(i).GetLogicalVolume()
        register_sensitive_detector_to_childs(actor, child)
