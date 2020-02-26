import logging
from anytree import Node, RenderTree

log=logging.getLogger(__name__)

def fatal(s):
    log.fatal(s)
    exit()

def raise_except(s):
    #s = colored.stylize(s, color_error)
    raise Exception(s)

def pretty_print_tree(tree, geometry):
    ''' Print tree '''
    s = ''
    for pre, fill, node in RenderTree(tree['world']):
        v = geometry[node.name]
        s += f'{pre}{node.name} {v.type} {v.material}\n'

    # remove last break line
    return s[:-1]

