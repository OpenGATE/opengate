from box import Box
import gam
import gam_g4 as g4
from anytree import Node


class Geometry(g4.G4VUserDetectorConstruction):
    """
    Implementation of G4VUserDetectorConstruction.
    In 'Construct' function, build all volumes in the scene.
    Keep a list of solid, logical volumes, physical volumes, materials.
    """

    def __init__(self, geometry):
        """
        Class that store geometry description.
        self.geometry is the dict that describes all parameters
        self.geometry_tree is the volumes sorted as a tree
        other are g4 objects
        """
        g4.G4VUserDetectorConstruction.__init__(self)
        self.geometry = geometry
        self.geometry_tree = None
        self.g4_solid_volumes = Box()
        self.g4_logical_volumes = Box()
        self.g4_physical_volumes = Box()
        self.g4_materials = Box()
        self.g4_NistManager = None

    def __del__(self):
        # it seems that phys_XXX should be delete here, before the auto delete.
        # it not, sometimes, it seg fault after the simulation end
        # So we build another list to del all elements except the World
        self.g4_physical_volumes = [v for v in self.g4_physical_volumes if v != 'World']

    def Construct(self):
        # tree re-order
        self.check_geometry()
        self.geometry_tree = self.build_tree()

        # material
        self.g4_NistManager = g4.G4NistManager.Instance()
        self.g4_materials.Air = self.g4_NistManager.FindOrBuildMaterial('G4_AIR')
        self.g4_materials.Water = self.g4_NistManager.FindOrBuildMaterial('G4_WATER')

        for volname in self.geometry:
            vol = self.geometry[volname]
            p = self.construct_volume(vol)
            self.g4_physical_volumes[vol.name] = p

        return self.g4_physical_volumes.World

    def dump_tree(self):
        if not self.geometry_tree:
            gam.fatal(f'Cannot dump geometry tree because it is not yet constructed.'
                      f' Use simulation.initialize() first')
        return gam.pretty_print_tree(self.geometry_tree, self.geometry)

    def construct_volume(self, vol):
        """
        -> standard build, other build functions will build complex vol (voxelized, repeater)
        """
        solid = g4.G4Box(vol.name,  # name
                         vol.size[0] / 2.0, vol.size[1] / 2.0, vol.size[2] / 2.0)  # half size in mm
        material = self.g4_materials[vol.material]
        logical = g4.G4LogicalVolume(solid,  # solid
                                     material,  # material
                                     vol.name)  # name
        if vol.mother:
            mother_logical = self.g4_logical_volumes[vol.mother]
        else:
            mother_logical = None
        if 'translation' not in vol:
            vol.translation = g4.G4ThreeVector()
        physical = g4.G4PVPlacement(None,  # no rotation
                                    g4.G4ThreeVector(vol.translation[0], vol.translation[1], vol.translation[2]),  #
                                    logical,  # logical volume
                                    vol.name,
                                    mother_logical,  # no mother volume
                                    False,  # no boolean operation
                                    0,  # copy number
                                    True)  # overlaps checking
        self.g4_solid_volumes[vol.name] = solid
        self.g4_logical_volumes[vol.name] = logical

        return physical

    def check_geometry(self):
        names = {}
        for v in self.geometry:
            vol = self.geometry[v]

            # volume must have a name
            if 'name' not in vol:
                gam.fatal(f"Volume is missing a 'name' = {vol}")

            # volume name must be geometry name
            if v != vol.name:
                gam.fatal(f"Volume named '{v}' in geometry has a different name = {vol}")

            # volume must have a type
            if 'type' not in vol:
                gam.fatal(f"Volume is missing a 'type' = {vol}")

            if vol.name in names:
                gam.fatal(f"Two volumes have the same name '{vol.name}' --> {self}")
            names[vol.name] = True

            # volume must have a mother, default is 'world'
            if 'mother' not in vol:
                vol.mother = 'world'

            # volume must have a material
            # (maybe to remove, i.e. voxelized ?)
            if 'material' not in vol:
                gam.fatal(f"Volume is missing a 'material' = {vol}")
                # vol.material = 'air'

    def build_tree(self):
        # world is needed as the root
        if 'World' not in self.geometry:
            s = f'No world in geometry = {self.geometry}'
            gam.fatal(s)

        # build the root tree (needed)
        tree = {'World': Node('World')}
        self.geometry.World.already_done = True

        # build the tree
        for v in self.geometry:
            vol = self.geometry[v]
            if 'already_done' in vol:
                continue
            self.add_volume_to_tree(tree, vol)

        # remove the already_done key
        for v in self.geometry:
            del self.geometry[v].already_done

        return tree

    def add_volume_to_tree(self, tree, vol):
        # check if mother volume exists
        if vol.mother not in self.geometry:
            gam.fatal(f"Cannot find a mother volume named '{vol.mother}', for the volume {vol}")

        vol.already_done = 'in_progress'
        m = self.geometry[vol.mother]

        # check for the cycle
        if 'already_done' not in m:
            self.add_volume_to_tree(tree, m)
        else:
            if m.already_done == 'in_progress':
                s = f'Error while building the tree, there is a cycle ? '
                s += f'\n volume is {vol}'
                s += f'\n parent is {m}'
                gam.fatal(s)

        # get the mother branch
        p = tree[m.name]

        # check not already exist
        if vol.name in tree:
            s = f'Node already exist in tree {vol.name} -> {tree}'
            s = s + f'\n Probably two volumes with the same name ?'
            gam.fatal(s)

        # create the node
        n = Node(vol.name, parent=p)
        tree[vol.name] = n
        vol.already_done = True
