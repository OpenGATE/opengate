from box import Box
import opengate as gate
import opengate_core as g4
from copy import copy

from ..helpers import fatal, indent
import Volumes

""" Global name for the world volume"""
__world_name__ = "world"


class VolumeManager:
    """
    Store and manage a hierarchical list of geometrical volumes and associated materials.
    This tree will be converted into Geant4 Solid/PhysicalVolume/LogicalVolumes
    """

    volume_types = {}
    volume_types["BoxVolume"] = Volumes.BoxVolume
    volume_types["SphereVolume"] = Volumes.SphereVolume
    volume_types["TrapVolume"] = Volumes.TrapVolume
    volume_types["ImageVolume"] = Volumes.ImageVolume
    volume_types["TubsVolume"] = Volumes.TubsVolume
    volume_types["PolyhedraVolume"] = Volumes.PolyhedraVolume
    volume_types["HexagonVolume"] = Volumes.HexagonVolume
    volume_types["ConsVolume"] = Volumes.ConsVolume
    volume_types["TrdVolume"] = Volumes.TrdVolume
    volume_types["BooleanVolume"] = Volumes.BooleanVolume
    volume_types["RepeatParametrisedVolume"] = Volumes.RepeatParametrisedVolume

    def __init__(self, simulation):
        """
        Class that store geometry description.
        """
        self.simulation = simulation

        # world name by default (will be changed if parallel world)
        self.world_name = __world_name__

        # list of all parallel worlds (must be ordered)
        self.parallel_world_names = []

        self.volumes = {}

        # OBSOLETE
        # # list of all user_info describing the volumes
        # self.volumes_user_info = {}  # user info only

        # database of materials
        self.material_database = gate.MaterialDatabase()

        # FIXME maybe store solids ?

    def __del__(self):
        # print("del volume manager")
        pass

    def __str__(self):
        s = f"{len(self.volumes_user_info)} volumes"
        return s

    def _simulation_engine_closing(self):
        """This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.

        """
        self.material_database = None
        self.user_info_volumes = None

    def __getstate__(self):
        """
        This is important : to get actor's outputs from a simulation run in a separate process,
        the class must be serializable (pickle).
        The g4 material databases and the volumes_user_info containing volume from solid have to be removed first.

        """
        dict_to_return = dict(self.__dict__)
        dict_to_return["material_database"] = {}
        dict_to_return["volumes_user_info"] = {}
        return dict_to_return

    def get_volume_depth(self, volume_name):
        depth = 0
        current = self.volumes[volume_name]
        while current.name != "world":
            current = self.volumes[current.mother]
            depth += 1
        return depth

    def add_parallel_world(self, name):
        if name in self.parallel_world_names:
            gate.fatal(
                f"Cannot create the parallel world named {name} because it already exists"
            )
        self.parallel_world_names.append(name)

    def get_volume_world(self, volume_name):
        try:
            vol = self.volumes[volume_name]
        except KeyError:
            gate.fatal(f"Cannot find the volume {volume_name}")
        if vol.mother is None or vol.mother == self.world_name:
            return self.world_name
        elif vol.mother in self.parallel_world_names:
            return vol.mother
        else:
            return self.get_volume_world(vol.mother)

    def add_volume(self, vol_type, name):
        # check that another element with the same name does not already exist
        if name in self.volumes.keys():
            fatal(
                f"The volume name {name} already exists. Exisiting volume names are: {self.volumes.keys()}"
            )
        if vol_type not in self.volume_types.keys():
            fatal(
                f"Unknown volume type {vol_type}. Known types are: {self.volume_types.keys()}."
            )

        self.volumes[name] = self.volume_types[vol_type](name=name)
        return self.volumes[name]

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
            fatal(f'Database "{filename}" already exist.')
        self.material_database.read_from_file(filename)

    def dump_volumes(self):
        s = f"Number of volumes: {len(self.volumes)}"
        for vol in self.volumes.values():
            s += indent(2, f"\n{vol}")
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
