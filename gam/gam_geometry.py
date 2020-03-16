from gam_helpers import *
import colored
from box import Box
from anytree import Node, RenderTree
from gam_solid import *

def create_geometry_tree(geometry):

    # world is needed as the root
    if 'world' not in geometry:
        s = f'No world in geometry = {geometry}'
        raise_except(s)

    # build the root tree (needed)
    tree = {}
    tree['world'] = Node('world')
    geometry.world.already_done = True

    # build the tree
    for v in geometry:
        vol = geometry[v]
        if 'already_done' in vol:
            continue
        add_volume_to_tree(geometry, tree, vol)

    # remove the already_done key
    for v in geometry:
        del geometry[v].already_done
        
    return tree


def check_geometry(geometry):
    names = {}
    for v in geometry:
        vol = geometry[v]
        
        # volume must have a name 
        if 'name' not in vol:
            raise_except(f"Volume is missing a 'name' = {vol}")

        # volume name must be geometry name
        if v != vol.name:
            raise_except(f"Volume named '{v}' in geometry has a different name = {vol}")

        # volume must have a type
        if 'type' not in vol:
            raise_except(f"Volume is missing a 'type' = {vol}")

        if vol.name in names:
            raise_except(f"Two volumes have the same name '{vol.name}' --> {geometry}")
        names[vol.name] = True
            
        # volume must have a mother
        if 'mother' not in vol:
            vol.mother = 'world'

        # volume must have a material
        if 'material' not in vol:
            vol.material = 'air'


def add_volume_to_tree(geometry, tree, vol):

    # check if mother volume exists
    if vol.mother not in geometry:
        raise_except(f"Cannot find a mother volume named '{vol.mother}', for the volume {vol}")

    vol.already_done = 'in_progress'
    m = geometry[vol.mother]

    # check for the cycle
    if 'already_done' not in m:
        add_volume_to_tree(geometry, tree, m)
    else:
        if m.already_done == 'in_progress':
            s = f'Error while building the tree, there is a cycle ? '
            s += f'\n volume is {vol}'
            s += f'\n parent is {m}'
            raise_except(s)

    # get the mother branch
    p = tree[m.name]

    # check not already exist
    if vol.name in tree:
        s = f'Node already exist in tree {vol.name} -> {tree}'
        s = s+f'\n Probably two volumes with the same name ?'
        raise_except(s)

    # create the node
    n = Node(vol.name, parent=p)
    tree[vol.name] = n
    vol.already_done = True


    
def build_volume_VERSION1(vol):
    """
    Version1: build a volume (solid + LV + PV) without class
    """

    # create the solid
    if vol.type not in g_solid_builders:
        s = f"The volume type '{vol.type}' is unknown."
        raise_except(s)
    solid_builder = g_solid_builders[vol.type]
    solid = solid_builder(vol)

    # get the material
    print('material is {vol.material}')
    # material = g_theMaterialDatabase.GetMaterial(mMaterialName);
    #  G4NistManager* nist = G4NistManager::Instance();
    # G4Material* env_mat = nist->FindOrBuildMaterial("G4_WATER");
    nist = Geant4.G4NistManager.Instance()
    material = nist.FindOrBuildMaterial(vol.material)
    print(material)

    # create the logical volume
    log_vol_name = vol.name+'_log_vol'
    log_vol = Geant4.G4LogicalVolume(solid, material, log_vol_name)
    print(log_vol)

    # Region

    # Sensitive Detector

    # Visu attribute

    # Construct child ???? -> not needed ?

    # Surface info ?

    # placement modification (origin ?) ### FIXME ?

    # 
    rotation_matrix = Geant4.G4RotationMatrix() # G4RotationMatrix
    position = vol.position ## G4ThreeVector
    phys_vol_name = vol.name+'_phys_vol'

    # get mother volume (must have been created before)
    # mother_log_vol = geometry[vol.mother].g4.log_vol
    # OR by GEANT4 ?
    s = Geant4.G4LogicalVolumeStore.GetInstance()
    mother_log_vol = s.GetVolume(vol.mother, verbose=True)

    # physical volume ; repeater,
    phys_vol = Geant4.G4PVPlacement(rotation_matrix,          # rotation with respect to its mother volume
                                    position,                 # translation with respect to its mother volume
                                    log_vol,                  # the associated logical volume
                                    phys_vol_name,            # physical volume name
                                    mother_log_vol,           # the mother logical volume
                                    False,                    # for future use,, can be set to false
                                    copyNumber,               # copy number
                                    overlap_check_flag)       # false/true = no/yes overlap check triggered
    print(phys_vol)

    # store some G4 elements
    vol.g4 = Box()
    vol.g4.solid = solid
    vol.g4.material = material
    vol.g4.log_vol = log_vol
    vol.g4.phys_vol = phys_vol
    
