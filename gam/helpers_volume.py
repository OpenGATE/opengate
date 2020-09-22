from .BoxSolidBuilder import *
from .SphereSolidBuilder import *
from .TrapSolidBuilder import *

solid_builders = {
    'Box': BoxSolidBuilder(),
    'Sphere': SphereSolidBuilder(),
    'Trap': TrapSolidBuilder()
}

# G4Tubs G4CutTubs G4Cons G4Para G4Trd
# G4Trap G4Torus (G4Orb not needed) G4Tet
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
