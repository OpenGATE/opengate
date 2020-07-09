import logging
import colored
import numpy as np
import geant4 as g4
from anytree import RenderTree

color_error = colored.fg("red") + colored.attr("bold")
color_warning = colored.fg("orange_1")
color_ok = colored.fg("green")

log = logging.getLogger(__name__)


def ok(s):
    s = colored.stylize(s, color_ok)
    print(s)
    exit(0)


def fatal(s):
    s = colored.stylize(s, color_error)
    print(s)
    exit(-1)


def warning(s):
    s = colored.stylize(s, color_warning)
    print(s)


def raise_except(s):
    s = colored.stylize(s, color_error)
    raise Exception(s)


def pretty_print_tree(tree, geometry):
    ''' Print tree '''
    s = ''
    for pre, fill, node in RenderTree(tree['World']):
        v = geometry[node.name]
        s += f'{pre}{node.name} {v.type} {v.material}\n'

    # remove last break line
    return s[:-1]


def test_dict(d1, d2, name=''):
    for k in d1:
        if not k in d2:
            fatal(f'ERROR missing key {k} in {name}')
        if isinstance(d1[k], np.ndarray):
            if np.any(d2[k] != d1[k]):
                fatal(f'ERROR np array {k} {d1[k]} in {name}')
        else:
            if d2[k] != d1[k]:
                fatal(f'ERROR value for {k} in {name}')
    for k in d2:
        if not k in d1:
            fatal(f'ERROR, additional key {k} in {name}')


def g4_units(name):
    table = g4.G4UnitDefinition.GetUnitsTable()
    for t in table:
        for a in t.GetUnitsList():
            if a.GetName() == name or a.GetSymbol() == name:
                return a.GetValue()
    list = []
    for t in table:
        for a in t.GetUnitsList():
            list.append(a.GetSymbol())
    s = [ str(l)+' ' for l in list]
    fatal(f'Error, cannot find the unit named {name}. Known are: {s}')


