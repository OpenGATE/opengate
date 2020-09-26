from box import Box
import gam
import gam_g4 as g4
from anytree import Node


class VolumeManager(g4.G4VUserDetectorConstruction):
    """
    Implementation of G4VUserDetectorConstruction.
    In 'Construct' function, build all volumes in the scene.
    Keep a list of solid, logical volumes, physical volumes, materials.
    """

    def __init__(self, volumes_info):
        """
        Class that store geometry description.
        self.geometry is the dict that describes all parameters
        self.geometry_tree is the volumes sorted as a tree
        other are g4 objects
        """
        g4.G4VUserDetectorConstruction.__init__(self)
        self.volumes_info = volumes_info
        self.volumes_tree = None
        self.volumes = {}
        self.is_construct = False
        self.g4_solid_volumes = Box()
        self.g4_logical_volumes = Box()
        self.g4_physical_volumes = Box()
        self.g4_materials = Box()
        self.g4_NistManager = None
        self.material_databases = {}
        self.element_names = []
        self.material_names = []

    def __del__(self):
        # print('geometry manager destructor')
        # it seems that phys_XXX should be delete here, before the auto delete.
        # it not, sometimes, it seg fault after the simulation end
        # So we build another list to del all elements except the World
        self.g4_physical_volumes = [v for v in self.g4_physical_volumes if v != 'World']

    def dump(self, level=0):
        self.check_geometry()
        self.volumes_tree = self.build_tree()
        s = ''
        if self.is_construct:
            s = 'Geometry is constructed'
        else:
            s = 'Geometry is NOT yet constructed '
        s += '\n' + self.dump_tree()
        if level > 0:
            if self.is_construct:
                for vol in self.volumes_info:
                    s += gam.indent(2, f'\n{str(self.volumes[vol])}')
            else:
                for vol in self.volumes_info:
                    s += gam.indent(2, f'\n{self.volumes_info[vol]}')
        return s

    def Construct(self):
        """
        Override the Construct method from G4VUserDetectorConstruction
        """
        if self.is_construct:
            gam.fatal('Cannot construct volumes, it has been already done.')
        # tree re-order
        self.check_geometry()
        self.volumes_tree = self.build_tree()

        # default material database: NIST
        self.g4_NistManager = g4.G4NistManager.Instance()
        self.material_databases['NIST'] = self.g4_NistManager
        self.element_names = self.g4_NistManager.GetNistElementNames()
        self.material_names = self.g4_NistManager.GetNistMaterialNames()

        # check for duplicate material names
        # not sure needed
        for db in self.material_databases:
            if db == 'NIST':
                continue
            for m in self.material_databases[db].material_builders:
                if m in self.material_names:
                    gam.fatal(f'Error in db {db}, the material {m} is already defined')
                self.material_names.append(m)
            for m in self.material_databases[db].element_builders:
                if m in self.element_names:
                    gam.fatal(f'Error in db {db}, the element {m} is already defined')
                self.element_names.append(m)

        # build volumes tree
        for vol_name in self.volumes_info:
            vol = self.volumes[vol_name]
            vol.construct(self)
            self.g4_physical_volumes[vol_name] = vol.g4_physical_volume

        # return self.g4_physical_volumes.World
        self.is_construct = True
        return self.volumes['World'].g4_physical_volume

    def dump_tree(self):
        if not self.volumes_tree:
            gam.fatal(f'Cannot dump geometry tree because it is not yet constructed.'
                      f' Use simulation.initialize() first')
        return gam.pretty_print_tree(self.volumes_tree, self.volumes_info)

    def dump_defined_material(self, level):
        table = g4.G4Material.GetMaterialTable
        if level == 0:
            names = [m.GetName() for m in table]
            return names
        return table

    def check_geometry(self):
        names = {}
        for v in self.volumes_info:
            vol = self.volumes_info[v]

            # volume must have a name
            if 'name' not in vol:
                gam.fatal(f"Volume is missing a 'name' : {vol}")

            # volume name must be geometry name
            if v != vol.name:
                gam.fatal(f"Volume named '{v}' in geometry has a different name : {vol}")

            # volume must have a type
            if 'type' not in vol:
                gam.fatal(f"Volume is missing a 'type' : {vol}")

            if vol.name in names:
                gam.fatal(f"Two volumes have the same name '{vol.name}' --> {self}")
            names[vol.name] = True

            # volume must have a mother, default is 'world'
            if 'mother' not in vol:
                vol.mother = 'world'

            # volume must have a material
            # (maybe to remove, i.e. voxelized ?)
            if 'material' not in vol:
                gam.fatal(f"Volume is missing a 'material' : {vol}")
                # vol.material = 'air'

    def build_tree(self):
        # world is needed as the root
        if 'World' not in self.volumes_info:
            s = f'No world in geometry = {self.volumes_info}'
            gam.fatal(s)

        # build the root tree (needed)
        tree = {'World': Node('World')}
        self.volumes_info.World.already_done = True

        # build the tree
        for v in self.volumes_info:
            vol = self.volumes_info[v]
            if 'already_done' in vol:
                continue
            self.add_volume_to_tree(tree, vol)

        # remove the already_done key
        for v in self.volumes_info:
            del self.volumes_info[v].already_done

        return tree

    def add_volume_to_tree(self, tree, vol):
        # check if mother volume exists
        if vol.mother not in self.volumes_info:
            gam.fatal(f"Cannot find a mother volume named '{vol.mother}', for the volume {vol}")

        vol.already_done = 'in_progress'
        m = self.volumes_info[vol.mother]

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

    def add_material_database(self, filename, name):
        if not name:
            name = filename
        if name in self.material_databases:
            gam.fatal(f'Database "{name}" already exist.')
        db = gam.MaterialDatabase(filename)
        self.material_databases[name] = db

    def check_overlaps(self):
        for v in self.g4_physical_volumes.keys():
            w = self.g4_physical_volumes[v]
            b = w.CheckOverlaps(1000, 0, True, 1)
            if b:
                gam.fatal(f'Some volumes overlap. Abort')

    def find_or_build_material(self, material):
        # loop on all databases
        found = False
        mat_db = None
        mat = None
        for db_name in self.material_databases:
            db = self.material_databases[db_name]
            m = db.FindOrBuildMaterial(material)
            if m and not found:
                found = True
                mat = m
                mat_db = db_name
                break
        if not found:
            gam.fatal(f'Cannot find the material {material}')
        # need a object to store the material without destructor
        self.g4_materials[material] = mat
        return mat
