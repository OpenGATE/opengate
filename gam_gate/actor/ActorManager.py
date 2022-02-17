import gam_gate as gam
from gam_gate import log


class ActorManager:
    """
    Manage all the actors in the simulation
    """

    def __init__(self, simulation):
        self.simulation = simulation
        self.user_info_actors = {}
        self.actors = {}
        self.action_manager = None

    def __str__(self):
        v = [v.name for v in self.user_info_actors.values()]
        s = f'{" ".join(v)} ({len(self.user_info_actors)})'
        return s

    def __del__(self):
        pass

    def dump(self):
        n = len(self.user_info_actors)
        s = f'Number of Actors: {n}'
        for actor in self.user_info_actors.values():
            if n > 1:
                a = '\n' + '-' * 20
            else:
                a = ''
            a += f'\n {actor}'
            s += gam.indent(2, a)
        return s

    def get_actor(self, name):
        if name not in self.actors:
            gam.fatal(f'The actor {name} is not in the current '
                      f'list of actors: {self.actors}')
        return self.actors[name]

    def add_actor(self, actor_type, name):
        # check that another element with the same name does not already exist
        gam.assert_unique_element_name(self.user_info_actors, name)
        # build it
        a = gam.UserInfo('Actor', actor_type, name)
        # append to the list
        self.user_info_actors[name] = a
        # return the info
        return a

    def create_actors(self, action_manager):
        self.action_manager = action_manager
        for ui in self.user_info_actors.values():
            actor = gam.new_element(ui, self.simulation)
            log.debug(f'Actor: initialize [{ui.type_name}] {ui.name}')
            actor.initialize()
            self.actors[ui.name] = actor

    def initialize(self):
        # consider the priority value of the actors
        l = [{'name': l, 'priority': self.actors[l].user_info.priority} for l in self.actors]
        sorted_actors = sorted(l, key=lambda d: d['priority'])
        # for actor in self.actors.values():
        for ac in sorted_actors:
            actor = self.actors[ac['name']]
            log.debug(f'Actor: initialize [{actor.user_info.type_name}] {actor.user_info.name}')
            self.register_all_actions(actor)
            # warning : the step actions will be registered by register_sensitive_detectors
            # called by ConstructSDandField

    def register_all_actions(self, actor):
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
                continue
            # Step: only enabled if attachTo a given volume.
            # Propagated to all child and sub-child
            tree = self.simulation.volume_manager.volumes_tree
            mothers = actor.user_info.mother
            if isinstance(mothers, str):
                # make a list with one single element
                mothers = [mothers]
            # add SD for all mothers
            for vol in mothers:
                if vol not in tree:
                    s = f'Cannot attach the actor {actor.user_info.name} ' \
                        f'because the volume {vol} does not exists'
                    gam.fatal(s)
                # Propagate the Geant4 Sensitive Detector to all children
                lv = self.simulation.volume_manager.volumes[vol].g4_logical_volume
                self.register_sensitive_detector_to_childs(actor, lv)

    def register_sensitive_detector_to_childs(self, actor, lv):
        log.debug(f'Actor: "{actor.user_info.name}" '
                  f'(attached to "{actor.user_info.mother}") '
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
