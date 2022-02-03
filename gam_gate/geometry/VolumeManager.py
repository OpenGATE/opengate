from box import Box
import gam_gate as gam
import gam_g4 as g4
from anytree import Node

""" Global name for the world volume"""
__world_name__ = 'world'


class VolumeManager(g4.G4VUserDetectorConstruction):
    """
    Implementation of G4VUserDetectorConstruction.
    In 'Construct' function, build all volumes in the scene.
    Keep a list of solid, logical volumes, physical volumes, materials.
    """

    def __init__(self, simulation):
        """
        Class that store geometry description.
        self.geometry is the dict that describes all parameters
        self.geometry_tree is the volumes sorted as a tree
        other are g4 objects
        """
        g4.G4VUserDetectorConstruction.__init__(self)
        self.simulation = simulation
        # list of all user_info describing the volumes
        self.user_info_volumes = {}  # user info only
        self.volumes_tree = None
        # list of all build volumes (only after initialization
        self.volumes = {}
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
        pass

    def __str__(self):
        s = f'{len(self.user_info_volumes)} volumes,' \
            f' {len(self.volumes)} are constructed'
        return s

    def get_volume_info(self, name):
        if name not in self.user_info_volumes:
            gam.fatal(f'The volume {name} is not in the current '
                      f'list of volumes: {self.user_info_volumes}')
        return self.user_info_volumes[name]

    def get_volume(self, name, check_initialization=True):
        if check_initialization and not self.is_constructed:
            gam.fatal(f'Cannot get_volume before initialization')
        if name not in self.volumes:
            gam.fatal(f'The volume {name} is not in the current '
                      f'list of volumes: {self.volumes}')
        return self.volumes[name]

    def new_solid(self, solid_type, name):
        if solid_type == 'Boolean':
            gam.fatal(f'Cannot create solid {solid_type}')
        # Create a UserInfo for a volume
        u = gam.UserInfo('Volume', solid_type, name)
        # remove unused keys: object, etc (it's a solid, not a volume)
        VolumeManager._pop_keys_unused_by_solid(u)
        return u

    def get_solid_info(self, user_info):
        """
        Temporary build a solid from the user info, in order to retrieve information (volume etc).
        Can be used *before* initialization
        """
        vol = gam.new_element(user_info, self.simulation)
        vol = vol.build_solid()
        r = Box()
        r.cubic_volume = vol.GetCubicVolume()
        r.surface_area = vol.GetSurfaceArea()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        vol.BoundingLimits(pMin, pMax)
        r.bounding_limits = [pMin, pMax]
        return r

    def _pop_keys_unused_by_solid(user_info):
        # remove unused keys: object, etc (it's a solid, not a volume)
        u = user_info.__dict__
        u.pop('mother', None)
        u.pop('translation', None)
        u.pop('color', None)
        u.pop('rotation', None)
        u.pop('material', None)

    def add_volume(self, vol_type, name):
        # check that another element with the same name does not already exist
        gam.assert_unique_element_name(self.user_info_volumes, name)
        # initialize the user_info
        v = gam.UserInfo('Volume', vol_type, name)
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
        # if isinstance(solid, Box): ### FIXME
        for op in gam.bool_operators:
            try:
                if op in solid:
                    v = self.add_volume('Boolean', name)
                    v.solid = solid
            except:
                pass
        if not v:
            v = self.add_volume(solid.type_name, name)
            # copy the parameters of the solid
            gam.vol_copy(solid, v)
        return v

    def add_material_database(self, filename, name):
        if not name:
            name = filename
        if name in self.material_databases:
            gam.fatal(f'Database "{name}" already exist.')
        db = gam.MaterialDatabase(filename, self.material_databases)
        self.material_databases[name] = db

    def Construct(self):
        """
        Override the Construct method from G4VUserDetectorConstruction
        """
        if self.is_constructed:
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
        # (not sure needed)
        for db in self.material_databases:
            if db == 'NIST':
                continue
            for m in self.material_databases[db].material_builders:
                if m in self.material_names:
                    gam.warning(f'Error in db {db}, the material {m} is already defined. Ignored.')
                else:
                    self.material_names.append(m)
            for m in self.material_databases[db].element_builders:
                if m in self.element_names:
                    gam.warning(f'Error in db {db}, the element {m} is already defined. Ignored.')
                else:
                    self.element_names.append(m)

        # build all real volumes object
        for vu in self.user_info_volumes.values():
            # create the volume
            vol = gam.new_element(vu, self.simulation)
            # construct the G4 Volume
            vol.construct(self)
            if len(vol.g4_physical_volumes) == 0:
                vol.g4_physical_volumes.append(vol.g4_physical_volume)
            # keep the volume
            self.volumes[vu.name] = vol

        # return self.g4_physical_volumes.world
        self.is_constructed = True
        return self.volumes[gam.__world_name__].g4_physical_volume

    def dump(self):
        self.check_geometry()
        self.volumes_tree = self.build_tree()
        s = f'Number of volumes: {len(self.user_info_volumes)}'
        s += '\n' + self.dump_tree()
        for vol in self.user_info_volumes.values():
            s += gam.indent(2, f'\n{vol}')
        return s

    def dump_tree(self):
        self.volumes_tree = self.build_tree()
        info = {}
        for v in self.user_info_volumes.values():
            info[v.name] = v
        return gam.pretty_print_tree(self.volumes_tree, info)

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
            if 'name' not in vol.__dict__:
                gam.fatal(f"Volume is missing a 'name' : {vol}")

            # volume name must be geometry name
            if v != vol.name:
                gam.fatal(f"Volume named '{v}' in geometry has a different name : {vol}")

            # volume must have a type
            # FIXME
            # if 'type' not in vol:
            #    gam.fatal(f"Volume is missing a 'type' : {vol}")

            if vol.name in names:
                gam.fatal(f"Two volumes have the same name '{vol.name}' --> {self}")
            names[vol.name] = True

            # volume must have a mother, default is gam.__world_name__
            if 'mother' not in vol.__dict__:
                vol.mother = gam.__world_name__

            # volume must have a material
            if 'material' not in vol.__dict__:
                gam.fatal(f"Volume is missing a 'material' : {vol}")
                # vol.material = 'air'

    def build_tree(self):
        # world is needed as the root
        if gam.__world_name__ not in self.user_info_volumes:
            s = f'No world in geometry = {self.user_info_volumes}'
            gam.fatal(s)

        # build the root tree (needed)
        tree = {gam.__world_name__: Node(gam.__world_name__)}
        already_done = {gam.__world_name__: True}

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
                        gam.fatal(f'Some volumes overlap the volume "{v}". \n'
                                  f'Consider using G4 verbose to know which ones. \n'
                                  f'Aborting.')
                except:
                    pass
                    # gam.warning(f'do not check physical volume {w}')

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
            gam.fatal(f'Cannot find the material {material}')
        # need a object to store the material without destructor
        self.g4_materials[material] = mat
        return mat

    # G4 overloaded
    def ConstructSDandField(self):
        # This function is called in MT mode
        self.simulation.actor_manager.register_sensitive_detectors()

    def _add_volume_to_tree(self, already_done, tree, vol):
        # check if mother volume exists
        if vol.mother not in self.user_info_volumes:
            gam.fatal(f"Cannot find a mother volume named '{vol.mother}', for the volume {vol}")

        already_done[vol.name] = 'in_progress'
        m = self.user_info_volumes[vol.mother]

        # check for the cycle
        if m.name not in already_done:
            self._add_volume_to_tree(already_done, tree, m)
        else:
            if already_done[m.name] == 'in_progress':
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
        already_done[vol.name] = True
