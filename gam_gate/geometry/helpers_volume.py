from .BoxVolume import *
from .SphereVolume import *
from .TrapVolume import *
from .ImageVolume import *
from .TubsVolume import *
from .ConsVolume import *
from .PolyhedraVolume import *
from .TrdVolume import *
from .BooleanVolume import *
from .RepeatParametrisedVolume import *
import copy
import os

volume_type_names = {BoxVolume,
                     SphereVolume,
                     TrapVolume,
                     ImageVolume,
                     TubsVolume,
                     PolyhedraVolume,
                     ConsVolume,
                     TrdVolume,
                     BooleanVolume,
                     RepeatParametrisedVolume}
volume_builders = gam.make_builders(volume_type_names)

# G4Tubs G4CutTubs G4Cons G4Para G4Trd
# G4Torus (G4Orb not needed) G4Tet
# G4EllipticalTube G4Ellipsoid G4EllipticalCone
# G4Paraboloid G4Hype
# specific: G4Polycone G4GenericPolycone Polyhedra
# G4ExtrudedSolid G4TwistedBox G4TwistedTrap G4TwistedTrd G4GenericTrap
# G4TwistedTubs

"""
http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html#constructed-solid-geometry-csg-solids
"""


def read_voxel_materials(filename, def_mat='G4_AIR'):
    p = os.path.abspath(filename)
    f = open(p, 'r')
    current = 0
    materials = []
    for line in f:
        for word in line.split():
            if word[0] == '#':
                break
            if current == 0:
                start = float(word)
                current = 1
            else:
                if current == 1:
                    stop = float(word)
                    current = 2
                else:
                    if current == 2:
                        mat = word
                        current = 0
                        materials.append([start, stop, mat])

    # sort according to starting interval
    materials = sorted(materials)

    # consider all values
    pix_mat = []
    previous = None
    for m in materials:
        if previous and previous > m[0]:
            gam.fatal(f'Error while reading {filename}\n'
                      f'Intervals are not disjoint: {previous} {m}')
        if m[0] > m[1]:
            gam.fatal(f'Error while reading {filename}\n'
                      f'Wrong interval {m}')
        if not previous or previous == m[0]:
            pix_mat.append([m[1], m[2]])
            previous = m[1]
        else:
            pix_mat.append([m[0], def_mat])
            pix_mat.append([m[1], m[2]])
            previous = m[1]

    return pix_mat


def vol_copy(v1, v2):
    """
    Copy all attributes from v1 to v2, except the name.
    v1 is assumed to be a UserInfo object with several attribute members.
    v2 must have the (at least) the same set of attributes.
    Values are (deep) copied.
    """
    for k in v1.__dict__:
        if k == 'name':
            continue
        setattr(v2, k, copy.deepcopy(v1.__dict__[k]))


def new_material(name, density, elements, weights=[1]):
    n = g4.G4NistManager.Instance()
    if not isinstance(elements, list):
        elements = [elements]
    if len(elements) != len(weights):
        gam.fatal(f'Cannot create the new material, the elements and the '
                  f'weights does not have the same size: {elements} and {weights}')
    total = np.sum(weights)
    weights = weights / total
    m = n.ConstructNewMaterialWeights(name, elements, weights, density)
    return m


def box_add_size(box, thickness):
    box.size = [x + thickness for x in box.size]


def cons_add_size(cons, thickness):
    cons.rmax1 += thickness / 2
    cons.rmax2 += thickness / 2
    cons.dz += thickness


def copy_solid_with_thickness(simulation, solid, thickness):
    s = simulation.new_solid(solid.type_name, f'{solid.name}_thick')
    vol_copy(solid, s)
    types = {'Box': box_add_size,
             'Cons': cons_add_size}
    types[s.type_name](s, thickness)
    return s


def get_max_size_from_volume(simulation, volume_name):
    v = simulation.get_volume_user_info(volume_name)
    s = simulation.get_solid_info(v)
    pMin = s.bounding_limits[0]
    pMax = s.bounding_limits[1]
    return [pMax[0] - pMin[0], pMax[1] - pMin[1], pMax[2] - pMin[2]]
