from anytree import PreOrderIter
import opengate_core as g4
from ..helpers import warning, fatal
from ..EngineBase import EngineBase


class VolumeEngine(g4.G4VUserDetectorConstruction, EngineBase):
    """
    Engine that will create all G4 elements for the hierarchy of volumes.
    Correspond to the G4VUserDetectorConstruction (inherit)
    Also manage the list of parallel worlds.
    """

    def __init__(self, simulation_engine):
        g4.G4VUserDetectorConstruction.__init__(self)
        EngineBase.__init__(self)

        self.simulation_engine = simulation_engine
        self.is_constructed = False

        # short cut reference
        self.volume_manager = self.simulation_engine.simulation.volume_manager

        self.parallel_world_engines = {}
        # create the parallel worlds constructors
        self.initialize_parallel_worlds()
        # set this VolumeEngine as the volume_engine in each volume
        self.initialize_volumes()

    def close(self):
        for vol in self.volume_manager.volumes.values():
            vol.close()
        for pwv in self.volume_manager.parallel_world_volumes.values():
            pwv.close()
        self.volume_manager.world_volume.close()

    def initialize_parallel_worlds(self):
        for parallel_world_name in self.volume_manager.parallel_world_names:
            self.parallel_world_engines[parallel_world_name] = ParallelWorldEngine(
                parallel_world_name, self
            )
            self.RegisterParallelWorld(self.parallel_world_engines[parallel_world_name])

    def initialize_volumes(self):
        self.volume_manager.update_volume_tree()
        for volume in PreOrderIter(self.volume_manager.world_volume):
            print(f"DEBUG: construct volume {volume.name}, {type(volume)}")
            volume.volume_engine = self

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserDetectorConstruction
        """

        # Construct all volumes within the mass world along the tree hierarchy
        # The world volume is the first item
        for volume in PreOrderIter(self.volume_manager.world_volume):
            print(f"DEBUG: construct volume {volume.name}, {type(volume)}")
            volume.construct()

        # return the (main) world physical volume
        self.is_constructed = True
        return self.volume_manager.world_volume.g4_physical_volume

    def check_overlaps(self, verbose):
        for volume in self.volume_manager.volumes.values():
            for pw in volume.g4_physical_volumes:
                try:
                    b = pw.CheckOverlaps(1000, 0, verbose, 1)
                    if b:
                        fatal(
                            f'Some volumes overlap with the volume "{volume.name}". \n'
                            f"Use Geant4's verbose output to know which ones. \n"
                            f"Aborting."
                        )
                except:
                    warning(f"Could not check overlap for volume {volume.name}.")

    # Short cut to method in volume manager
    def find_or_build_material(self, material):
        return self.simulation_engine.simulation.volume_manager.find_or_build_material(
            material
        )

    def ConstructSDandField(self):
        """
        G4 overloaded
        """
        # FIXME
        # This function is called in MT mode
        self.simulation_engine.actor_engine.register_sensitive_detectors(
            self.volume_manager.world_volume.name,
        )

    def get_volume(self, name):
        try:
            return self.volume_manager.volumes[name]
        except KeyError:
            fatal(
                f"The volume {name} was not found."
                f"Volumes included in this simulation are: {self.volume_manager.volumes}"
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


class ParallelWorldEngine(g4.G4VUserParallelWorld, EngineBase):
    """
    FIXME
    """

    def __init__(self, parallel_world_name, volume_engine):
        g4.G4VUserParallelWorld.__init__(self, parallel_world_name)
        EngineBase.__init__(self)

        # keep input data
        self.volume_engine = volume_engine
        self.parallel_world_name = parallel_world_name

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserParallelWorld
        """

        parallel_world_volume = (
            self.volume_engine.volume_manager.parallel_world_volumes[
                self.parallel_world_name
            ]
        )
        # the parallel world volume needs the engine to construct itself
        parallel_world_volume.parallel_world_engine = self
        # Construct all volumes within this world along the tree hierarchy
        # The world volume of this world is the first item
        for volume in PreOrderIter(parallel_world_volume):
            volume.construct()

    def ConstructSD(self):
        # FIXME
        self.volume_engine.simulation_engine.actor_engine.register_sensitive_detectors(
            self.parallel_world_name,
        )
