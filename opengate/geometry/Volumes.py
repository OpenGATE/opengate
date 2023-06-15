from .VolumeBase import VolumeBase
from .Solids import (
    BoxSolid,
    HexagonSolid,
    ConsSolid,
    PolyhedraSolid,
    SphereSolid,
    TrapSolid,
    TrdSolid,
    TubsSolid,
)


class BoxVolume(VolumeBase, BoxSolid):
    """Volume with a box shape."""


class HexagonVolume(VolumeBase, HexagonSolid):
    """Volume with a hexagon shape."""


class ConsVolume(VolumeBase, ConsSolid):
    """Volume with a the shape of a cone or conical section."""


class PolyhedraVolume(VolumeBase, PolyhedraSolid):
    """Volume with a polyhedral shape."""


class SphereVolume(VolumeBase, SphereSolid):
    """Volume with a sphere or spherical shell shape."""


class TrapVolume(VolumeBase, TrapSolid):
    """Volume with a generic trapezoidal shape."""


class TrdVolume(VolumeBase, TrdSolid):
    """Volume with a symmetric trapezoidal shape."""


class TubsVolume(VolumeBase, TubsSolid):
    """Volume with a tube or cylindrical section shape."""
