import logging
import colored
from anytree import Node, RenderTree

color_error = colored.fg("red") + colored.attr("bold")
color_warning = colored.fg("orange_1")

log=logging.getLogger(__name__)

def fatal(s):
    s = colored.stylize(s, color_error)
    print(s)
    exit(0)

def warning(s):
    s = colored.stylize(s, color_warning)
    print(s)

def raise_except(s):
    s = colored.stylize(s, color_error)
    raise Exception(s)

def pretty_print_tree(tree, geometry):
    ''' Print tree '''
    s = ''
    for pre, fill, node in RenderTree(tree['world']):
        v = geometry[node.name]
        s += f'{pre}{node.name} {v.type} {v.material}\n'

    # remove last break line
    return s[:-1]

