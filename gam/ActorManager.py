import gam
from gam import log


class ActorManager:
    """
    Manage all the actors in the simulation
    """

    def __init__(self, simulation):
        self.simulation = simulation
        self.actors = {}
        self.action_manager = None

    def __str__(self):
        v = [v.user_info.name for v in self.actors.values()]
        s = f'{" ".join(v)} ({len(self.actors)})'
        return s

    def __del__(self):
        print('ActorManager destructor')

    def dump(self):
        n = len(self.actors)
        s = f'Number of Actors: {len(self.actors)}'
        for actor in self.actors.values():
            if n > 1:
                a = '\n' + '-' * 20
            else:
                a = ''
            a += f'\n {actor.user_info}'
            s += gam.indent(2, a)
        return s

    def get_actor(self, name):
        if name not in self.actors:
            gam.fatal(f'The actor {name} is not in the current '
                      f'list of actors: {self.actors}')
        return self.actors[name]

    def add_actor(self, actor_type, name):
        # check that another element with the same name does not already exist
        gam.assert_unique_element_name(self.actors, name)
        # build it
        a = gam.new_element('Actor', actor_type, name, self.simulation)
        # append to the list
        self.actors[name] = a
        # return the info
        return a.user_info

    def initialize(self, action_manager):
        self.action_manager = action_manager
        for actor in self.actors.values():
            log.debug(f'Actor: initialize [{actor.user_info.type}] {actor.user_info.name}')
            actor.initialize()
            self.register_actions(actor)

    def register_actions(self, actor):
        # Run
        for ra in self.action_manager.g4_RunAction:
            ra.RegisterActor(actor)
        # Event
        for ea in self.action_manager.g4_EventAction:
            ea.RegisterActor(actor)
        # Track
        for ta in self.action_manager.g4_TrackingAction:
            ta.RegisterActor(actor)
        # initialization
        actor.ActorInitialize()

    def register_sensitive_detectors(self):
        for actor in self.actors.values():
            if not 'SteppingAction' in actor.fActions:
                print('No stepping action for ', actor)
                continue
            # Step: only enabled if attachTo a given volume.
            # Propagated to all child and sub-child
            tree = self.simulation.volume_manager.volumes_tree
            vol = actor.user_info.attached_to
            if vol not in tree:
                s = f'Cannot attach the actor {actor.user_info.name} ' \
                    f'because the volume {vol} does not exists'
                gam.fatal(s)
            # Propagate the Geant4 Sensitive Detector to all childs
            lv = self.simulation.volume_manager.volumes[vol].g4_logical_volume
            self.register_sensitive_detector_to_childs(actor, lv)

    def register_sensitive_detector_to_childs(self, actor, lv):
        log.debug(f'Actor: "{actor.user_info.name}" '
                  f'(attached to "{actor.user_info.attached_to}") '
                  f'set to volume "{lv.GetName()}"')
        actor.RegisterSD(lv)
        n = lv.GetNoDaughters()
        for i in range(n):
            child = lv.GetDaughter(i).GetLogicalVolume()
            self.register_sensitive_detector_to_childs(actor, child)

    def start_simulation(self):
        for actor in self.actors.values():
            actor.StartSimulationAction()

    def stop_simulation(self):
        for actor in self.actors.values():
            actor.EndSimulationAction()
