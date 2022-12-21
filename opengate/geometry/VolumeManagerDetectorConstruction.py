from box import Box
import opengate as gate
import opengate_core as g4
from anytree import Node


class VolumeManagerDetectorConstruction(g4.G4VUserDetectorConstruction):
    def __init__(self, simulation, volume_manager):
        g4.G4VUserDetectorConstruction.__init__(self)
        self.volume_manager = volume_manager

        self.simulation = simulation
        self.is_constructed = False
        # G4 elements are stored to avoid auto destruction
        # and allows access
        self.g4_materials = Box()
        # Materials databases
        self.g4_NistManager = None
        self.material_databases = {}
        self.element_names = []
        self.material_names = []

    def __del__(self):
        print("del VolumeManagerDetectorConstruction")
        pass

    def check_geometry(self):
        names = {}
        for v in self.volumes:
            vol = self.volumes[v].user_info

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

            # volume must have a mother, default is gate.__world_name__
            if "mother" not in vol.__dict__:
                vol.mother = gate.__world_name__

            # volume must have a material
            if "material" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'material' : {vol}")
                # vol.material = 'air'

    def build_tree(self):
        # world is needed as the root
        if gate.__world_name__ not in self.user_info_volumes:
            s = f"No world in geometry = {self.user_info_volumes}"
            gate.fatal(s)

        # build the root tree (needed)
        tree = {gate.__world_name__: Node(gate.__world_name__)}
        already_done = {gate.__world_name__: True}

        # build the tree
        for vol in self.user_info_volumes.values():
            if vol.name in already_done:
                continue
            self._add_volume_to_tree(already_done, tree, vol)

        return tree

    def Construct(self):
        """
        Override the Construct method from G4VUserDetectorConstruction
        """
        vm = self.volume_manager
        self.volumes = vm.volumes
        self.user_info_volumes = vm.user_info_volumes

        if self.is_constructed:
            gate.fatal("Cannot construct volumes, it has been already done.")

        # tree re-order
        self.check_geometry()
        self.volumes_tree = self.build_tree()

        # default material database: NIST
        self.g4_NistManager = g4.G4NistManager.Instance()
        self.material_databases["NIST"] = self.g4_NistManager
        self.element_names = self.g4_NistManager.GetNistElementNames()
        self.material_names = self.g4_NistManager.GetNistMaterialNames()

        # check for duplicate material names
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

        # build all real volumes object
        for vu in self.user_info_volumes.values():
            # create the volume
            vol = gate.new_element(vu, self.simulation)
            # construct the G4 Volume
            vol.construct(self)
            if len(vol.g4_physical_volumes) == 0:
                vol.g4_physical_volumes.append(vol.g4_physical_volume)
            # keep the volume
            self.volumes[vu.name] = vol

        # return self.g4_physical_volumes.world
        self.is_constructed = True
        return self.volumes[gate.__world_name__].g4_physical_volume

    def dump(self):
        self.check_geometry()
        self.volumes_tree = self.build_tree()
        s = f"Number of volumes: {len(self.user_info_volumes)}"
        s += "\n" + self.dump_tree()
        for vol in self.user_info_volumes.values():
            s += gate.indent(2, f"\n{vol}")
        return s

    def dump_tree(self):
        self.volumes_tree = self.build_tree()
        info = {}
        for v in self.user_info_volumes.values():
            info[v.name] = v
        return gate.pretty_print_tree(self.volumes_tree, info)

    def dump_defined_material(self, level):
        table = g4.G4Material.GetMaterialTable
        if level == 0:
            names = [m.GetName() for m in table]
            return names
        return table

    def check_geometry(self):
        names = {}
        for v in self.volumes:
            vol = self.volumes[v].user_info

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

            # volume must have a mother, default is gate.__world_name__
            if "mother" not in vol.__dict__:
                vol.mother = gate.__world_name__

            # volume must have a material
            if "material" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'material' : {vol}")
                # vol.material = 'air'

    def build_tree(self):
        # world is needed as the root
        if gate.__world_name__ not in self.user_info_volumes:
            s = f"No world in geometry = {self.user_info_volumes}"
            gate.fatal(s)

        # build the root tree (needed)
        tree = {gate.__world_name__: Node(gate.__world_name__)}
        already_done = {gate.__world_name__: True}

        # build the tree
        for vol in self.user_info_volumes.values():
            if vol.name in already_done:
                continue
            self._add_volume_to_tree(already_done, tree, vol)

        return tree

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

    # G4 overloaded
    def ConstructSDandField(self):
        # This function is called in MT mode
        tree = self.volumes_tree
        self.simulation.actor_manager.register_sensitive_detectors(tree)

    def _add_volume_to_tree(self, already_done, tree, vol):
        # check if mother volume exists
        if vol.mother not in self.user_info_volumes:
            gate.fatal(
                f"Cannot find a mother volume named '{vol.mother}', for the volume {vol}"
            )

        already_done[vol.name] = "in_progress"
        m = self.user_info_volumes[vol.mother]

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
