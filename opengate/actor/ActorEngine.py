import opengate_core.opengate_core
import opengate as gate
from opengate import log
import weakref


class ActorEngine(gate.EngineBase):
    """
    This object manages all actors G4 objects at runtime
    """

    def __init__(self, simulation_engine):
        gate.EngineBase.__init__(self, simulation_engine)
        # self.actor_manager = simulation.actor_manager
        # we use a weakref because it is a circular dependence
        # with custom __del__
        self.simulation_engine_wr = weakref.ref(simulation_engine)
        self.actors = {}

    def __del__(self):
        if self.verbose_destructor:
            gate.warning("Deleting ActorEngine")

    def close(self):
        if self.verbose_close:
            gate.warning(f"Closing ActorEngine")
        for actor in self.actors.values():
            actor.close()
        self.actors = None

    def get_actor(self, name):
        if name not in self.actors:
            gate.fatal(
                f"The actor {name} is not in the current "
                f"list of actors: {self.actors}"
            )
        return self.actors[name]

    def create_actors(self):
        for (
            ui
        ) in (
            self.simulation_engine_wr().simulation.actor_manager.user_info_actors.values()
        ):
            actor = gate.new_element(ui, self.simulation_engine_wr().simulation)
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
        for ra in self.simulation_engine_wr().action_engine.g4_RunAction:
            ra.RegisterActor(actor)
        # Event
        for ea in self.simulation_engine_wr().action_engine.g4_EventAction:
            ea.RegisterActor(actor)
        # Track
        for ta in self.simulation_engine_wr().action_engine.g4_TrackingAction:
            ta.RegisterActor(actor)
        # initialization
        actor.ActorInitialize()

    def register_sensitive_detectors(
        self, world_name, tree, volume_manager, volume_engine
    ):
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)

        for actor in sorted_actors:
            if "SteppingAction" not in actor.fActions:
                continue

            # Step: only enabled if attachTo a given volume.
            # Propagated to all child and sub-child
            # tree = volume_manager.volumes_tree
            mothers = actor.user_info.mother
            if isinstance(mothers, str):
                # make a list with one single element
                mothers = [mothers]
            # add SD for all mothers
            for vol in mothers:
                vol_world = volume_manager.get_volume_world(vol)
                if vol_world != world_name:
                    # this actor is attached to a volume in another world
                    continue
                if vol not in tree:
                    s = (
                        f"Cannot attach the actor {actor.user_info.name} "
                        f"because the volume {vol} does not exists"
                    )
                    gate.fatal(s)
                # Propagate the Geant4 Sensitive Detector to all children
                n = f"{world_name}_{vol}"
                if world_name == gate.__world_name__:
                    n = vol
                lv = volume_engine.g4_volumes[n].g4_logical_volume
                self.register_sensitive_detector_to_child(actor, lv)

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
