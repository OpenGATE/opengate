from .gam_volume import *


def geometry_initialize(geometry):
    print(f'Building geometry')

    # check
    geometry_check(geometry)

    # build tree
    tree = geometry_create_tree(geometry)
    s = pretty_print_tree(tree, geometry)
    print(f'{s}')

    # build the volumes in the tree order
    for v in tree:
        geometry_build_volume(geometry[v])


def geometry_create_tree(geometry):
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
        geometry_add_volume_to_tree(geometry, tree, vol)

    # remove the already_done key
    for v in geometry:
        del geometry[v].already_done
        
    return tree


def geometry_check(geometry):
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
            
        # volume must have a mother, default is 'world'
        if 'mother' not in vol:
            vol.mother = 'world'

        # volume must have a material
        # (maybe to remove, i.e. voxelized ?)
        if 'material' not in vol:
            raise_except(f"Volume is missing a 'material' = {vol}")
            # vol.material = 'air'


def geometry_add_volume_to_tree(geometry, tree, vol):

    # check if mother volume exists
    if vol.mother not in geometry:
        raise_except(f"Cannot find a mother volume named '{vol.mother}', for the volume {vol}")

    vol.already_done = 'in_progress'
    m = geometry[vol.mother]

    # check for the cycle
    if 'already_done' not in m:
        geometry_add_volume_to_tree(geometry, tree, m)
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

