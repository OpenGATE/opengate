from .ParallelVolumeEngine import *
from copy import copy
from anytree import PreOrderIter
from ..helpers import warning, fatal


class VolumeEngine(g4.G4VUserDetectorConstruction, gate.EngineBase):
    """
    Engine that will create all G4 elements for the hierarchy of volumes.
    Correspond to the G4VUserDetectorConstruction (inherit)
    Also manage the list of parallel worlds.
    """

    def __init__(self, simulation_engine):
        g4.G4VUserDetectorConstruction.__init__(self)
        gate.EngineBase.__init__(self)

        self.simulation_engine = simulation_engine
        self.is_constructed = False

        # short cut reference
        self.volume_manager = self.simulation_engine.simulation.volume_manager

        self.parallel_world_engines = {}
        # create the parallel worlds constructors
        self.initialize_parallel_worlds()

    def close(self):
        for vol in self.volume_manager.volumes.values():
            vol.close()
        for pwv in self.volume_manager.parallel_world_volumes.values():
            pwv.close()
        self.volume_manager.world_volume.close()

    def initialize_parallel_worlds(self):
        for world_name in self.volume_manager.parallel_world_names:
            self.parallel_world_engines[world_name] = ParallelWorldEngine(
                world_name, self
            )
        self.RegisterParallelWorld(self.parallel_world_engines[world_name])

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserDetectorConstruction
        """

        # Construct all volumes within the mass world along the tree hierarchy
        # The world volume is the first item
        for volume in PreOrderIter(self.volume_manager.world_volume):
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
        tree = self.volumes_tree
        self.simulation_engine.actor_engine.register_sensitive_detectors(
            gate.__world_name__,
            tree,
            self.simulation_engine.simulation.volume_manager,
            self,
        )

    def get_volume(self, name, check_initialization=True):
        try:
            return self.volume_manager.volumes[name]
        except KeyError:
            gate.fatal(
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


class ParallelWorldEngine(g4.G4VUserParallelWorld, gate.EngineBase):
    """
    FIXME
    """

    def __init__(self, world_name, volume_engine):
        g4.G4VUserParallelWorld.__init__(self, world_name)
        gate.EngineBase.__init__(self)

        # keep input data
        self.volume_engine = volume_engine
        self.world_name = world_name

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserParallelWorld
        """

        world_volume = self.volume_engine.volume_manager.parallel_world_volumes[
            self.world_name
        ]
        # the parallel world volume needs the engine to construct itself
        world_volume.parallel_world_engine = self
        # Construct all volumes within this world along the tree hierarchy
        # The world volume of this world is the first item
        for volume in PreOrderIter(world_volume):
            volume.construct()

    def ConstructSD(self):
        # FIXME
        tree = self.volumes_tree
        self.volume_engine.simulation_engine.actor_engine.register_sensitive_detectors(
            self.world_name,
            tree,
            self.volume_engine.simulation_engine.simulation.volume_manager,
            self.volume_engine,
        )
