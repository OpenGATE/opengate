from anytree import RenderTree, NodeMixin, LoopError

from .MaterialDatabase import MaterialDatabase
from ..helpers import fatal, warning, indent, g4_units
from .Volumes import (
    VolumeBase,
    BoxVolume,
    SphereVolume,
    TrapVolume,
    ImageVolume,
    TubsVolume,
    PolyhedraVolume,
    HexagonVolume,
    ConsVolume,
    TrdVolume,
    BooleanVolume,
    RepeatParametrisedVolume,
    ParallelWorldVolume,
)
from .Volumes import __world_name__


class VolumeManager:
    """
    Store and manage a hierarchical list of geometrical volumes and associated materials.
    This tree will be converted into Geant4 Solid/PhysicalVolume/LogicalVolumes
    """

    volume_types = {}
    volume_types["BoxVolume"] = BoxVolume
    volume_types["SphereVolume"] = SphereVolume
    volume_types["TrapVolume"] = TrapVolume
    volume_types["ImageVolume"] = ImageVolume
    volume_types["TubsVolume"] = TubsVolume
    volume_types["PolyhedraVolume"] = PolyhedraVolume
    volume_types["HexagonVolume"] = HexagonVolume
    volume_types["ConsVolume"] = ConsVolume
    volume_types["TrdVolume"] = TrdVolume
    volume_types["BooleanVolume"] = BooleanVolume
    volume_types["RepeatParametrisedVolume"] = RepeatParametrisedVolume

    def __init__(self, simulation):
        """
        Class that store geometry description.
        """
        self.simulation = simulation

        self.volume_tree_root = VolumeTreeRoot(
            volume_manager=self
        )  # abstract element used as common root for volume tree
        m = g4_units("meter")

        self.volumes = {}
        self.volumes[__world_name__] = BoxVolume(
            volume_manager=self,
            name=__world_name__,
            size=[3 * m, 3 * m, 3 * m],
            material="G4_AIR",
        )
        self.volumes[__world_name__].mother = None
        self.volumes[
            __world_name__
        ].parent = self.volume_tree_root  # attach the world to the tree
        self.parallel_world_volumes = {}

        self._need_tree_update = True  # flag to store state of volume tree

        # database of materials
        self.material_database = MaterialDatabase()

    def __str__(self):
        s = "**** Volume manager ****\n"
        if len(self.parallel_world_volumes) > 0:
            s += f"Number of parallel worlds: {len(self.parallel_world_volumes)}\n"
            s += f"Names of the parallel worlds: {self.parallel_world_names}\n"
        s += f"Number of volumes: {len(self.volumes)}\n"
        s += "The volumes are organized in the following hierarchy:\n"
        s += self.dump_volume_tree()
        return s

    @property
    def world_volume(self):
        return self.volumes[__world_name__]

    @property
    def world_volumes(self):
        """List of all world volumes, including the mass world volume."""
        world_volumes = [self.world_volume]
        world_volumes.extend(list(self.parallel_world_volumes.values()))
        return world_volumes

    @property
    def parallel_world_names(self):
        return [v.name for v in self.parallel_world_volumes]

    @property
    def all_volume_names(self):
        return list(self.volumes.keys())
        # names = [self.world_volume.name]
        # names.extend(self.parallel_world_names)
        # names.extend(list(self.volumes.keys()))
        # return names

    def update_volume_tree(self):
        if self._need_tree_update is True:
            for v in self.volumes.values():
                if v not in self.parallel_world_volumes and v is not self.world_volume:
                    try:
                        v._update_node()
                    except LoopError:
                        raise (
                            Exception(
                                f"There seems to be a loop in the volume tree involving volume {v.name}."
                            )
                        )
            self._need_tree_update = False

    def add_volume(self, volume):
        if not isinstance(volume, VolumeBase):
            fatal("Invalid kind of volume, unable to add it to the simulation.")
        if volume.name in self.all_volume_names:
            fatal(
                f"The volume name {volume.name} already exists. Exisiting volume names are: {self.volumes.keys()}"
            )
        self.volumes[volume.name] = volume
        self.volumes[volume.name].volume_manager = self
        self._need_tree_update = True

    def create_volume(self, volume_type, name):
        # check that another element with the same name does not already exist
        if name in self.all_volume_names:
            # only issue a warning because the volume is not added to the simulation
            # so there is no immediate risk of corruption
            # add_volume raises a fatal error instead
            warning(
                f"The volume name {name} already exists. Exisiting volume names are: {self.volumes.keys()}"
            )
        volume_type_variants = [volume_type, volume_type + "Volume"]
        for vt in volume_type_variants:
            if vt in self.volume_types.keys():
                return self.volume_types[vt](name=name)
        fatal(
            f"Unknown volume type {vt}. Known types are: {list(self.volume_types.keys())}."
        )

    def create_and_add_volume(self, volume_type, name):
        new_volume = self.create_volume(volume_type, name)
        self.add_volume(new_volume)
        return new_volume

    def add_parallel_world(self, name):
        if name in self.all_volume_names:
            fatal(
                f"Cannot create the parallel world named {name} because it already exists."
            )
        self.volumes[name] = ParallelWorldVolume(
            name, self
        )  # constructor needs self, i.e. the volume manager
        self.parallel_world_volumes[name] = self.volumes[name]
        self._need_tree_update = True

    def _simulation_engine_closing(self):
        """This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.

        """
        self.material_database = None

    def __getstate__(self):
        """
        This is important : to get actor's outputs from a simulation run in a separate process,
        the class must be serializable (pickle).
        The g4 material databases and the volumes_user_info containing volume from solid have to be removed first.

        """
        self.material_database = {}
        return self.__dict__

    def find_or_build_material(self, material):
        return self.material_database.FindOrBuildMaterial(material)

    def add_material_database(self, filename):
        if filename in self.material_database.filenames:
            fatal(f'Database "{filename}" already exist.')
        self.material_database.read_from_file(filename)

    def dump_volumes(self):
        s = f"Number of volumes: {len(self.volumes)}"
        for vol in self.volumes.values():
            s += indent(2, f"\n{vol}")
        return s

    def dump_volume_tree(self):
        s = ""
        for pre, _, node in RenderTree(self.volume_tree_root):
            s += f"{pre}{node.name}"
            print("%s%s" % (pre, node.name))
        return s


# inherit from NodeMixin turn the class into a tree node
class VolumeTreeRoot(NodeMixin):
    """Small class to provide a root for the volume tree."""

    def __init__(self, volume_manager) -> None:
        super().__init__()
        self.volume_manager = volume_manager
        self.name = "volume_tree_root"
        self.parent = None  # None means this is a tree root

    def close(self):
        pass
