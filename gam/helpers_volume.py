from .BoxSolidBuilder import *
from .SphereSolidBuilder import *
from .TrapSolidBuilder import *
import os

solid_builders = {
    'Box': BoxSolidBuilder(),
    'Sphere': SphereSolidBuilder(),
    'Trap': TrapSolidBuilder(),
    'Image': BoxSolidBuilder()  # FIXME change this
}

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


def get_solid_builder(solid_type):
    if solid_type not in gam.solid_builders:
        s = f'Cannot find the solid type "{solid_type}".' \
            f' List of known solid types: '
        for t in gam.solid_builders:
            s += t + ' '
        gam.fatal(s)
    return gam.solid_builders[solid_type]


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
