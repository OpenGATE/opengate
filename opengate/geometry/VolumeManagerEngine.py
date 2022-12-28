from box import Box
import opengate as gate
import opengate_core as g4
from anytree import Node


class VolumeManagerEngine(g4.G4VUserDetectorConstruction):
    """

    FIXME

    """

    def __init__(self, simulation):
        g4.G4VUserDetectorConstruction.__init__(self)

        # keep input data
        self.volume_manager = simulation.volume_manager
        self.simulation = simulation
        self.is_constructed = False

        # tree of volumes
        self.volumes_tree = None
        self.g4_volumes = []

        # materials databases
        self.g4_NistManager = None
        self.g4_materials = Box()
        self.element_names = []
        self.material_names = []

    def __del__(self):
        print("del VolumeManagerEngine")
        pass

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserDetectorConstruction
        """

        # build the tree of volumes
        self.check_geometry()
        self.volumes_tree = self.build_tree()

        # default material database: NIST
        self.g4_NistManager = g4.G4NistManager.Instance()
        self.material_databases["NIST"] = self.g4_NistManager
        self.element_names = self.g4_NistManager.GetNistElementNames()
        self.material_names = self.g4_NistManager.GetNistMaterialNames()

        # check for duplicate material names
        self.check_materials()

        # build all G4 volume objects
        self.build_g4_volumes()

        # return the world physical volume
        self.is_constructed = True
        return self.volumes[gate.__world_name__].g4_physical_volume

    def check_geometry(self):
        names = {}
        volumes = self.volume_manager.volumes
        for v in volumes:
            vol = volumes[v].user_info

            # volume must have a name
            if "_name" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'name' : {vol}")

            # volume name must be geometry name
            if v != vol.name:
                gate.fatal(
                    f"Volume named '{v}' in geometry has a different name : {vol}"
                )

            if vol.name in names:
                gate.fatal(f"Two volumes have the same name '{vol.name}' --> {self}")
            names[vol.name] = True

            # volume must have a mother
            if "mother" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'mother' : {vol}")

            # volume must have a material
            if "material" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'material' : {vol}")

    def build_tree(self):
        # FIXME --> put elsewhere to make it callable before init
        # world is needed as the root
        uiv = self.volume_manager.user_info_volumes
        if gate.__world_name__ not in uiv:
            s = f"No world in geometry = {uiv}"
            gate.fatal(s)

        # build the root tree (needed)
        tree = {gate.__world_name__: Node(gate.__world_name__)}
        already_done = {gate.__world_name__: True}

        # build the tree
        for vol in uiv.values():
            if vol.name in already_done:
                continue
            self._add_volume_to_tree(already_done, tree, vol)

        return tree

    def _add_volume_to_tree(self, already_done, tree, vol):
        # check if mother volume exists
        uiv = self.volume_manager.user_info_volumes
        if vol.mother not in uiv:
            gate.fatal(
                f"Cannot find a mother volume named '{vol.mother}', for the volume {vol}"
            )

        already_done[vol.name] = "in_progress"
        m = uiv[vol.mother]

        # check for the cycle
        if m.name not in already_done:
            self._add_volume_to_tree(already_done, tree, m)
        else:
            if already_done[m.name] == "in_progress":
                s = f"Error while building the tree, there is a cycle ? "
                s += f"\n volume is {vol}"
                s += f"\n parent is {m}"
                gate.fatal(s)

        # get the mother branch
        p = tree[m.name]

        # check not already exist
        if vol.name in tree:
            s = f"Node already exist in tree {vol.name} -> {tree}"
            s = s + f"\n Probably two volumes with the same name ?"
            gate.fatal(s)

        # create the node
        n = Node(vol.name, parent=p)
        tree[vol.name] = n
        already_done[vol.name] = True

    def check_materials(self):
        # (not sure needed)
        for db in self.material_databases:
            if db == "NIST":
                continue
            for m in self.material_databases[db].material_builders:
                if m in self.material_names:
                    gate.warning(
                        f"Error in db {db}, the material {m} is already defined. Ignored."
                    )
                else:
                    self.material_names.append(m)
            for m in self.material_databases[db].element_builders:
                if m in self.element_names:
                    gate.warning(
                        f"Error in db {db}, the element {m} is already defined. Ignored."
                    )
                else:
                    self.element_names.append(m)

    def check_overlaps(self, verbose):
        for v in self.volumes.values():
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
        # loop on all databases
        found = False
        mat = None
        for db_name in self.material_databases:
            db = self.material_databases[db_name]
            m = db.FindOrBuildMaterial(material)
            if m and not found:
                found = True
                mat = m
                break
        if not found:
            gate.fatal(f"Cannot find the material {material}")
        # need an object to store the material without destructor
        self.g4_materials[material] = mat
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

    def ConstructSDandField(self):
        """
        G4 overloaded
        """
        # This function is called in MT mode
        tree = self.volumes_tree
        self.simulation.actor_manager.register_sensitive_detectors(tree)

    def get_volume(self, name, check_initialization=True):
        if check_initialization and not self.is_constructed:
            gate.fatal(f"Cannot get_volume before initialization")
        if name not in self.g4_volumes:
            gate.fatal(
                f"The volume {name} is not in the current "
                f"list of volumes: {self.g4_volumes}"
            )
        return self.g4_volumes[name]
