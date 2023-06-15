from box import Box

from ..GateObjects import GateObject
from ..helpers import fatal, warning
from opengate_core import G4ThreeVector


class SolidBase(GateObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.g4_solid = None

    def close(self):
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_solid = None

    def get_solid_info(self):
        """Computes the properties of the solid associated with this volume."""
        # Note: This method only works in derived classes which implement the build_solid method.
        solid = self.build_solid()
        if solid is None:
            fatal(
                "Cannot compute solid info for this volume {self.name}. Unable to build the solid."
            )
        r = Box()
        r.cubic_volume = solid.GetCubicVolume()
        r.surface_area = solid.GetSurfaceArea()
        pMin = G4ThreeVector()
        pMax = G4ThreeVector()
        solid.BoundingLimits(pMin, pMax)
        r.bounding_limits = [pMin, pMax]
        return r

    def bounding_limits(self):
        """
        Return the min and max 3D points of the bounding box of the given volume
        """
        pMin, pMax = self.get_solid_info().bounding_limits
        return pMin, pMax

    def bounding_box_size(self):
        """
        Return the size of the bounding box of the given volume
        """
        pMin, pMax = self.bounding_limits()
        return [pMax[0] - pMin[0], pMax[1] - pMin[1], pMax[2] - pMin[2]]

    def build_solid(self):
        s = (
            "Warning for developers: "
            f"Need to override 'build_solid' method in class {type(self).__name__}"
        )
        fatal(s)
