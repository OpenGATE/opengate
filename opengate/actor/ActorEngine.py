import opengate_core.opengate_core
import opengate as gate
from opengate import log
import weakref


class ActorEngine(gate.EngineBase):
    """
    FIXME
    """

    def __init__(self, actor_manager, simulation_engine):
        gate.EngineBase.__init__(self)
        self.actor_manager = actor_manager
        # we use a weakref because it is a circular dependence
        # with custom __del__
        self.simulation_engine_wr = weakref.ref(simulation_engine)
        # self.simulation_engine = simulation_engine
        self.action_engine = self.simulation_engine_wr().action_engine
        self.volume_engine = self.simulation_engine_wr().volume_engine
        self.actors = {}

    def __del__(self):
        if self.verbose_destructor:
            print("del ActorEngine")
        pass

    def get_actor(self, name):
        if name not in self.actors:
            gate.fatal(
                f"The actor {name} is not in the current "
                f"list of actors: {self.actors}"
            )
        return self.actors[name]

    def create_actors(self):
        for ui in self.actor_manager.user_info_actors.values():
            actor = gate.new_element(ui, self.actor_manager.simulation)
            log.debug(f"Actor: initialize [{ui.type_name}] {ui.name}")
            actor.initialize(self.simulation_engine_wr)
            self.actors[ui.name] = actor

    def initialize(self, volume_engine=None):
        # consider the priority value of the actors
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)
        # for actor in self.actors.values():
        for actor in sorted_actors:
            log.debug(
                f"Actor: initialize [{actor.user_info.type_name}] {actor.user_info.name}"
            )
            self.register_all_actions(actor)
            # warning : the step actions will be registered by register_sensitive_detectors
            # called by ConstructSDandField

    def register_all_actions(self, actor):
        # Run
        for ra in self.action_engine.g4_RunAction:
            ra.RegisterActor(actor)
        # Event
        for ea in self.action_engine.g4_EventAction:
            ea.RegisterActor(actor)
        # Track
        for ta in self.action_engine.g4_TrackingAction:
            ta.RegisterActor(actor)
        # initialization
        actor.ActorInitialize()

    def register_sensitive_detector_propagate(self, actor, vol):
        lvs = opengate_core.opengate_core.G4LogicalVolumeStore.GetInstance()
        lv = lvs.GetVolume(vol, False)
        for i in range(lv.GetNoDaughters()):
            da = lv.GetDaughter(i)
            self.register_sensitive_detector_to_child(actor, da.GetLogicalVolume())
            self.register_sensitive_detector_propagate(
                actor, da.GetLogicalVolume().GetName()
            )

    def register_sensitive_detectors(self, tree):
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)
        # for actor in self.actors.values():
        for actor in sorted_actors:
            if "SteppingAction" not in actor.fActions:
                continue
            # Step: only enabled if attachTo a given volume.
            # Propagated to all child and sub-child
            # tree = self.simulation.volume_manager.volumes_tree
            mothers = actor.user_info.mother
            if isinstance(mothers, str):
                # make a list with one single element
                mothers = [mothers]
            # add SD for all mothers
            for vol in mothers:
                if vol not in tree:
                    s = (
                        f"Cannot attach the actor {actor.user_info.name} "
                        f"because the volume {vol} does not exists"
                    )
                    gate.fatal(s)
                # Propagate the Geant4 Sensitive Detector to all children
                lv = self.volume_engine.g4_volumes[vol].g4_logical_volume
                self.register_sensitive_detector_to_child(actor, lv)

                # FIXME find all daughters ???
                # self.register_sensitive_detector_propagate(actor, vol)

    def register_sensitive_detector_to_child(self, actor, lv):
        log.debug(
            f'Actor: "{actor.user_info.name}" '
            f'(attached to "{actor.user_info.mother}") '
            f'set to volume "{lv.GetName()}"'
        )
        actor.RegisterSD(lv)
        n = lv.GetNoDaughters()
        for i in range(n):
            child = lv.GetDaughter(i).GetLogicalVolume()
            self.register_sensitive_detector_to_child(actor, child)

    def start_simulation(self):
        # consider the priority value of the actors
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)
        for actor in sorted_actors:
            actor.StartSimulationAction()

    def stop_simulation(self):
        # consider the priority value of the actors
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)
        for actor in sorted_actors:
            actor.EndSimulationAction()
