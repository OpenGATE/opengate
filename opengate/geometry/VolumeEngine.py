from .ParallelVolumeEngine import *


class VolumeEngine(g4.G4VUserDetectorConstruction, gate.EngineBase):
    """
    Engine that will create all G4 elements for the hierarchy of volumes.
    Correspond to the G4VUserDetectorConstruction (inherit)
    Also manage the list of parallel worlds.
    """

    def __init__(self, simulation_engine):
        g4.G4VUserDetectorConstruction.__init__(self)
        gate.EngineBase.__init__(self, simulation_engine)
        self.is_constructed = False

        # parallel world info
        self.world_volumes_user_info = {}
        self.parallel_volume_engines = []

        # list of volumes for the main world
        self.volumes_tree = None

        # all G4 volumes are store here
        # (including volumes in parallel worlds)
        self.g4_volumes = {}

        # create the parallel worlds
        self.initialize_parallel_worlds()

    def initialize_parallel_worlds(self):
        # init list of trees
        self.world_volumes_user_info = (
            self.simulation_engine.simulation.volume_manager.separate_parallel_worlds()
        )

        # build G4 parallel volume engine (except for main world)
        for world_name in self.world_volumes_user_info:
            if (
                world_name
                == self.simulation_engine.simulation.volume_manager.world_name
            ):
                continue
            # register a new parallel world
            volumes_user_info = self.world_volumes_user_info[world_name]
            pw = gate.ParallelVolumeEngine(self, world_name, volumes_user_info)
            self.RegisterParallelWorld(pw)
            # store it to avoid destruction
            self.parallel_volume_engines.append(pw)

    def __del__(self):
        if self.verbose_destructor:
            gate.warning("Deleting VolumeEngine")

    def close(self):
        if self.verbose_close:
            gate.warning(f"Closing VolumeEngine")
        for pwe in self.parallel_volume_engines:
            pwe.close()
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_volumes = None

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserDetectorConstruction
        """

        # build the materials
        self.simulation_engine.simulation.volume_manager.material_database.initialize()

        # initial check (not really needed)
        self.simulation_engine.simulation.check_geometry()

        # build the tree of volumes
        volumes_user_info = self.world_volumes_user_info[gate.__world_name__]
        self.volumes_tree = gate.build_tree(volumes_user_info)

        # build all G4 volume objects
        self.build_g4_volumes(volumes_user_info, None)

        # return the (main) world physical volume
        self.is_constructed = True
        return self.g4_volumes[gate.__world_name__].g4_physical_volume

    def check_overlaps(self, verbose):
        for v in self.g4_volumes.values():
            for w in v.g4_physical_volumes:
                try:
                    b = w.CheckOverlaps(1000, 0, verbose, 1)
                    if b:
                        gate.fatal(
                            f'Some volumes overlap the volume "{v}". \n'
                            f"Consider using G4 verbose to know which ones. \n"
                            f"Aborting."
                        )
                except:
                    pass
                    # gate.warning(f'do not check physical volume {w}')

    def find_or_build_material(self, material):
        mat = self.simulation_engine.simulation.volume_manager.material_database.FindOrBuildMaterial(
            material
        )
        return mat

    def build_g4_volumes(self, volumes_user_info, g4_world_log_vol):
        uiv = volumes_user_info
        for vu in uiv.values():
            # create the volume
            vol = gate.new_element(vu, self.simulation_engine.simulation)
            # construct the G4 Volume
            vol.construct(self, g4_world_log_vol)
            # store at least one PhysVol
            if len(vol.g4_physical_volumes) == 0:
                vol.g4_physical_volumes.append(vol.g4_physical_volume)
            # keep the volume to avoid being destructed
            if g4_world_log_vol is not None:
                n = f"{g4_world_log_vol.GetName()}_{vu.name}"
                self.g4_volumes[n] = vol
            else:
                self.g4_volumes[vu.name] = vol

    # def set_actor_engine(self, actor_engine):
    #     self.actor_engine = actor_engine
    #     for pw in self.parallel_volume_engines:
    #         pw.actor_engine = actor_engine

    def ConstructSDandField(self):
        """
        G4 overloaded
        """
        # This function is called in MT mode
        tree = self.volumes_tree
        self.simulation_engine.actor_engine.register_sensitive_detectors(
            gate.__world_name__,
            tree,
            self.simulation_engine.simulation.volume_manager,
            self,
        )

    def get_volume(self, name, check_initialization=True):
        if check_initialization and not self.is_constructed:
            gate.fatal(f"Cannot get_volume before initialization")
        try:
            return self.g4_volumes[name]
        except KeyError:
            gate.fatal(
                f"The volume {name} is not in the current "
                f"list of volumes: {self.g4_volumes}"
            )

    def get_database_material_names(self, db=None):
        return self.simulation_engine.simulation.volume_manager.material_database.get_database_material_names(
            db
        )

    def dump_build_materials(self, level=0):
        table = g4.G4Material.GetMaterialTable
        if level == 0:
            names = [m.GetName() for m in table]
            return names
        return table
