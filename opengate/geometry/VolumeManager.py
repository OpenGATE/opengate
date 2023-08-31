from box import Box
import opengate as gate
import opengate_core as g4
from copy import copy

""" Global name for the world volume"""
__world_name__ = "world"


class VolumeManager:
    """
    Store and manage a hierarchical list of geometrical volumes and associated materials.
    This tree will be converted into Geant4 Solid/PhysicalVolume/LogicalVolumes
    """

    def __init__(self, simulation):
        """
        Class that store geometry description.
        """
        self.simulation = simulation

        # world name by default (will be changed if parallel world)
        self.world_name = __world_name__

        # list of all parallel worlds (must be ordered)
        self.parallel_world_names = []

        # list of all user_info describing the volumes
        self.volumes_user_info = {}  # user info only

        # database of materials
        self.material_database = gate.MaterialDatabase()

    def __del__(self):
        if self.simulation.verbose_destructor:
            gate.warning("Deleting VolumeManager")

    def __str__(self):
        s = f"{len(self.volumes_user_info)} volumes"
        return s

    def _simulation_engine_closing(self):
        """
        This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.
        """
        self.material_database = None
        # self.volumes_user_info = None

    def get_volume_user_info(self, name):
        if name not in self.volumes_user_info:
            gate.fatal(
                f"The volume {name} is not in the current "
                f"list of volumes: {self.volumes_user_info}"
            )
        return self.volumes_user_info[name]

    def new_solid(self, solid_type, name):
        if solid_type == "Boolean":
            gate.fatal(f"Cannot create solid {solid_type}")
        # Create a UserInfo for a volume
        u = gate.UserInfo("Volume", solid_type, name)
        # remove unused keys: object, etc. (it's a solid, not a volume)
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

    def add_parallel_world(self, name):
        if name in self.parallel_world_names:
            gate.fatal(
                f"Cannot create the parallel world named {name} because it already exists"
            )
        self.parallel_world_names.append(name)

    def get_volume_world(self, volume_name):
        vol = self.get_volume_user_info(volume_name)
        if vol.mother is None or vol.mother == self.world_name:
            return self.world_name
        if vol.mother in self.parallel_world_names:
            return vol.mother
        if volume_name not in self.volumes_user_info:
            gate.fatal(f"Cannot find the volume {volume_name}")
        return self.get_volume_world(vol.mother)

    def add_volume(self, vol_type, name):
        # check that another element with the same name does not already exist
        gate.assert_unique_element_name(self.volumes_user_info, name)
        # initialize the user_info
        v = gate.UserInfo("Volume", vol_type, name)
        # add to the list
        self.volumes_user_info[name] = v
        # FIXME  NOT CLEAR --> here ? or later
        # create a region for the physics cuts
        # user will be able to set stuff like :
        # pm.production_cuts.my_volume.gamma = 1 * mm
        # pm = self.simulation.get_physics_user_info()
        # pm.production_cuts[name] = Box()
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

    def add_material_database(self, filename):
        if filename in self.material_database.filenames:
            gate.fatal(f'Database "{filename}" already exist.')
        self.material_database.read_from_file(filename)

    def dump_volumes(self):
        s = f"Number of volumes: {len(self.volumes_user_info)}"
        for vol in self.volumes_user_info.values():
            s += gate.indent(2, f"\n{vol}")
        return s

    def separate_parallel_worlds(self):
        world_volumes_user_info = {}
        # init list of trees
        world_volumes_user_info[self.world_name] = {}
        for w in self.parallel_world_names:
            world_volumes_user_info[w] = {}

        # loop to separate volumes for each world
        uiv = self.volumes_user_info
        for vu in uiv.values():
            world_name = self.get_volume_world(vu.name)
            world_volumes_user_info[world_name][vu.name] = vu

        # add a 'fake' copy of the real world volume to each parallel world
        # this is needed for build_tre
        the_world = world_volumes_user_info[gate.__world_name__][gate.__world_name__]
        for w in self.parallel_world_names:
            a = copy(the_world)
            a._name = w
            world_volumes_user_info[w][w] = a
        return world_volumes_user_info

    def dump_tree_of_volumes(self):  # FIXME put elsewhere
        world_volumes_user_info = self.separate_parallel_worlds()
        s = ""
        for w in world_volumes_user_info:
            vui = world_volumes_user_info[w]
            tree = gate.build_tree(vui, w)
            info = {}
            for v in vui.values():
                info[v.name] = v
            s += gate.render_tree(tree, info, w) + "\n"
        # remove last line break
        s = s[:-1]
        return s
