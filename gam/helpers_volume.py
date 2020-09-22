from .BoxSolidBuilder import *
from .SphereSolidBuilder import *

solid_builders = {
    'Box': BoxSolidBuilder(),
    'Sphere': SphereSolidBuilder(),
}

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
