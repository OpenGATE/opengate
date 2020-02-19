import colored
from anytree import Node, RenderTree


def raise_except(s):
    #s = colored.stylize(s, color_error)
    raise Exception(s)

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
        

def add_volume_to_tree(geometry, tree, vol):

    # volume must have a name 
    if 'name' not in vol:
        raise_except(f"Volume is missing a 'name' = {vol}")
            
    # volume must have a mother
    if 'mother' not in vol:
        # default mother volume is 'world'
        vol.mother = 'world'

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

