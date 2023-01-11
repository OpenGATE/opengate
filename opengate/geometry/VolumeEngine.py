from box import Box
import opengate as gate
import opengate_core as g4


class VolumeEngine(g4.G4VUserDetectorConstruction, gate.EngineBase):
    """
    FIXME
    """

    def __init__(self, simulation):
        g4.G4VUserDetectorConstruction.__init__(self)
        gate.EngineBase.__init__(self)

        # keep input data
        self.simulation = simulation
        self.volume_manager = simulation.volume_manager
        self.is_constructed = False
        self.actor_engine = None

        # tree of volumes
        self.volumes_tree = None
        self.g4_volumes = {}

    def __del__(self):
        if self.verbose_destructor:
            print("del VolumeEngine")
        pass

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserDetectorConstruction
        """

        # build the tree of volumes
        self.simulation.check_geometry()
        self.volumes_tree = gate.build_tree(self.simulation)

        # build all G4 volume objects
        self.build_g4_volumes()

        # return the world physical volume
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
        mat = self.volume_manager.material_database.FindOrBuildMaterial(material)
        return mat

    def build_g4_volumes(self):
        uiv = self.volume_manager.user_info_volumes
        for vu in uiv.values():
            # create the volume
            vol = gate.new_element(vu, self.simulation)
            # construct the G4 Volume
            vol.construct(self)
            if len(vol.g4_physical_volumes) == 0:
                vol.g4_physical_volumes.append(vol.g4_physical_volume)
            # keep the volume
            self.g4_volumes[vu.name] = vol

    def set_actor_engine(self, actor_engine):
        self.actor_engine = actor_engine

    def ConstructSDandField(self):
        """
        G4 overloaded
        """
        # This function is called in MT mode
        tree = self.volumes_tree
        self.actor_engine.register_sensitive_detectors(tree)

    def get_volume(self, name, check_initialization=True):
        if check_initialization and not self.is_constructed:
            gate.fatal(f"Cannot get_volume before initialization")
        if name not in self.g4_volumes:
            gate.fatal(
                f"The volume {name} is not in the current "
                f"list of volumes: {self.g4_volumes}"
            )
        return self.g4_volumes[name]

    def get_database_material_names(self, db=None):
        return self.volume_manager.material_database.get_database_material_names(db)

    def dump_build_materials(self, level=0):
        table = g4.G4Material.GetMaterialTable
        if level == 0:
            names = [m.GetName() for m in table]
            return names
        return table
