from box import Box
import opengate as gate
import opengate_core as g4
from anytree import Node

""" Global name for the world volume"""
__world_name__ = "world"


class VolumeManager:
    """
    Implementation of G4VUserDetectorConstruction.
    In 'Construct' function, build all volumes in the scene.
    Keep a list of solid, logical volumes, physical volumes, materials.
    """

    def __init__(self, simulation):
        """
        Class that store geometry description.
        """
        self.simulation = simulation

        # list of all user_info describing the volumes
        self.user_info_volumes = {}  # user info only

        # databases of materials
        self.user_material_databases = {}

        # FIXME maybe store solids ?

    def __del__(self):
        print("del volume manager")
        pass

    def __str__(self):
        s = f"{len(self.user_info_volumes)} volumes"
        return s

    def get_volume_user_info(self, name):
        if name not in self.user_info_volumes:
            gate.fatal(
                f"The volume {name} is not in the current "
                f"list of volumes: {self.user_info_volumes}"
            )
        return self.user_info_volumes[name]

    def new_solid(self, solid_type, name):
        if solid_type == "Boolean":
            gate.fatal(f"Cannot create solid {solid_type}")
        # Create a UserInfo for a volume
        u = gate.UserInfo("Volume", solid_type, name)
        # remove unused keys: object, etc (it's a solid, not a volume)
        VolumeManager._pop_keys_unused_by_solid(u)
        return u

    def get_solid_info(self, user_info):
        """
        Temporary build a solid from the user info, in order to retrieve information (volume etc).
        Can be used *before* initialization
        """
        vol = gate.new_element(user_info, self.simulation)
        vol = vol.build_solid()
        r = Box()
        r.cubic_volume = vol.GetCubicVolume()
        r.surface_area = vol.GetSurfaceArea()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        vol.BoundingLimits(pMin, pMax)
        r.bounding_limits = [pMin, pMax]
        return r

    def get_volume_depth(self, volume_name):
        depth = 0
        current = self.get_volume_user_info(volume_name)
        while current.name != "world":
            current = self.get_volume_user_info(current.mother)
            depth += 1
        return depth

    def _pop_keys_unused_by_solid(user_info):
        # remove unused keys: object, etc (it's a solid, not a volume)
        u = user_info.__dict__
        u.pop("mother", None)
        u.pop("translation", None)
        u.pop("color", None)
        u.pop("rotation", None)
        u.pop("material", None)

    def add_volume(self, vol_type, name):
        # check that another element with the same name does not already exist
        gate.assert_unique_element_name(self.user_info_volumes, name)
        # initialize the user_info
        v = gate.UserInfo("Volume", vol_type, name)
        # add to the list
        self.user_info_volumes[name] = v
        # FIXME  NOT CLEAR --> here ? or later
        # create a region for the physics cuts
        # user will be able to set stuff like :
        # pm.production_cuts.my_volume.gamma = 1 * mm
        pm = self.simulation.get_physics_user_info()
        cuts = pm.production_cuts
        cuts[name] = Box()
        # return the info
        return v

    def add_volume_from_solid(self, solid, name):
        v = None
        for op in gate.bool_operators:
            try:
                if op in solid:
                    v = self.add_volume("Boolean", name)
                    v.solid = solid
            except:
                pass
        if not v:
            v = self.add_volume(solid.type_name, name)
            # copy the parameters of the solid
            gate.copy_user_info(solid, v)
        return v

    def add_material_database(self, filename, name):
        if not name:
            name = filename
        if name in self.user_material_databases:
            gate.fatal(f'Database "{name}" already exist.')
        db = gate.MaterialDatabase(filename, self.user_material_databases)
        self.user_material_databases[name] = db

    def dump(self):
        self.check_geometry()
        self.volumes_tree = self.build_tree()  # FIXME todo
        s = f"Number of volumes: {len(self.user_info_volumes)}"
        s += "\n" + self.dump_tree()
        for vol in self.user_info_volumes.values():
            s += gate.indent(2, f"\n{vol}")
        return s

    def dump_tree(self):
        self.volumes_tree = self.build_tree()  # FIXME todo
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

    def find_or_build_material(self, material):
        # loop on all databases
        found = False
        mat = None
        for db_name in self.user_material_databases:
            db = self.user_material_databases[db_name]
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
