import opengate as gate
import opengate_core as g4


class ParallelVolumeEngine(g4.G4VUserParallelWorld, gate.EngineBase):
    """
    Volume engine for each parallel world
    """

    def __init__(self, volume_engine, world_name, volumes_user_info):
        g4.G4VUserParallelWorld.__init__(self, world_name)
        gate.EngineBase.__init__(self, volume_engine.simulation_engine)

        # keep input data
        self.volume_engine = volume_engine
        self.world_name = world_name
        self.volumes_user_info = volumes_user_info

        # G4 elements
        self.g4_world_phys_vol = None
        self.g4_world_log_vol = None

        # needed for ConstructSD
        self.volumes_tree = None

    def release_g4_references(self):
        self.g4_world_phys_vol = None
        self.g4_world_log_vol = None

    def close(self):
        if self.verbose_close:
            gate.warning(f"Closing ParallelVolumeEngine {self.world_name}")
        self.release_g4_references()

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserParallelWorld
        """

        # build the tree of volumes
        self.volumes_tree = gate.build_tree(self.volumes_user_info, self.world_name)

        # build the world Physical and Logical volumes
        self.g4_world_phys_vol = self.GetWorld()
        self.g4_world_log_vol = self.g4_world_phys_vol.GetLogicalVolume()

        # build all other volumes
        self.volume_engine.build_g4_volumes(
            self.volumes_user_info, self.g4_world_log_vol
        )

    def ConstructSD(self):
        tree = self.volumes_tree
        self.volume_engine.simulation_engine.actor_engine.register_sensitive_detectors(
            self.world_name,
            tree,
            self.volume_engine.simulation_engine.simulation.volume_manager,
            self.volume_engine,
        )
