from box import Box
import gam  # needed for gam_setup
import geant4 as g4
from anytree import Node, RenderTree


class Geometry(g4.G4VUserDetectorConstruction):
    """
    TODO
    """

    def __init__(self, geometry):
        """
        TODO
        """
        g4.G4VUserDetectorConstruction.__init__(self)
        self.geometry = geometry
        self.g4_solid_volumes = Box()
        self.g4_logical_volumes = Box()
        self.g4_physical_volumes = Box()
        self.g4_materials = Box()

    def __del__(self):
        print('===========================>  Geometry destructor')
        # del self.logic_waterbox
        # it seems that phys_waterbox should be delete here, before the auto delete.
        # it not, sometimes, it seg fault after the simulation end
        # if hasattr(self, 'phys_waterbox'):
        # FIXME
        del self.g4_physical_volumes.Waterbox
        # del self.g4_physical_volumes.World
        # del self.g4_logical_volumes.Waterbox
        # del self.g4_logical_volumes.World
        print('===========================>  Geometry destructor')

    def Construct(self):
        print('Geometry::Construct')

        # tree re-order
        self.check_geometry()
        self.geometry_tree = self.build_tree()
        s = gam.pretty_print_tree(self.geometry_tree, self.geometry)
        print(s)

        # material
        self.nist = g4.G4NistManager.Instance()
        self.g4_materials.Air = self.nist.FindOrBuildMaterial('G4_AIR')
        self.g4_materials.Water = self.nist.FindOrBuildMaterial('G4_WATER')

        for volname in self.geometry:
            vol = self.geometry[volname]
            p = self.construct_volume(vol)
            self.g4_physical_volumes[vol.name] = p

        return self.g4_physical_volumes.World

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
            print(v)
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
        tree = {}
        tree['World'] = Node('World')
        self.geometry.World.already_done = True

        # build the tree
        for v in self.geometry:
            vol = self.geometry[v]
            print(vol)
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
