from .BoxVolume import BoxVolume
from .SphereVolume import SphereVolume
from .TrapVolume import TrapVolume
from .ImageVolume import ImageVolume
from .TubsVolume import TubsVolume
from .ConsVolume import ConsVolume
from .PolyhedraVolume import PolyhedraVolume
from .HexagonVolume import HexagonVolume
from .TrdVolume import TrdVolume
from .RepeatParametrisedVolume import RepeatParametrisedVolume
from .BooleanVolume import BooleanVolume

from ..utility import make_builders


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

volume_type_names = {
    BoxVolume,
    SphereVolume,
    TrapVolume,
    ImageVolume,
    TubsVolume,
    PolyhedraVolume,
    HexagonVolume,
    ConsVolume,
    TrdVolume,
    RepeatParametrisedVolume,
    BooleanVolume,
}

volume_builders = make_builders(volume_type_names)
