from box import Box
import numpy as np

from opengate.GateObjects import GateObject
from opengate.helpers import fatal, warning, g4_units
import opengate_core as g4
from scipy.spatial.transform import Rotation


class SolidBase(GateObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.g4_solid = None
        # name of the volume in which this solid is used
        # needed to avoid duplicate use
        self._part_of_volume = None

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


class BooleanSolid(SolidBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator_solid_1 = None
        self.creator_solid_2 = None

    def close(self):
        super().close()
        if self.creator_solid_1 is not None:
            self.creator_solid_1.close()
        if self.creator_solid_2 is not None:
            self.creator_solid_2.close()

    def intersect_with(
        self, other_solid, translation=None, rotation=None, new_name=None
    ):
        return self._perform_operation(
            "intersect",
            other_solid,
            translation=translation,
            rotation=rotation,
            new_name=new_name,
        )

    def add_to(self, other_solid, translation=None, rotation=None, new_name=None):
        return self._perform_operation(
            "add",
            other_solid,
            translation=translation,
            rotation=rotation,
            new_name=new_name,
        )

    def substract_from(
        self, other_solid, translation=None, rotation=None, new_name=None
    ):
        return self._perform_operation(
            "subtract",
            other_solid,
            translation=translation,
            rotation=rotation,
            new_name=new_name,
        )

    def _perform_operation(
        self, operation, other_solid, translation=None, rotation=None, new_name=None
    ):
        if rotation is None:
            rotation = Rotation.identity().as_matrix()
        if translation is None:
            translation = [0, 0, 0]

        if other_solid.g4_solid is None:
            other_solid.build_solid()
        if self.g4_solid is None:
            self.build_solid()
        if operation == "intersect":
            new_g4_solid = g4.G4IntersectionSolid(
                new_name, other_solid, self, rotation, translation
            )
            name_joiner = "times"
        elif operation == "add":
            new_g4_solid = g4.G4UnionSolid(
                new_name, other_solid, self, rotation, translation
            )
            name_joiner = "plus"
        elif operation == "subtract":
            new_g4_solid = g4.G4SubtractionSolid(
                new_name, other_solid, self, rotation, translation
            )
            name_joiner = "minus"
        else:
            fatal("Unknown boolean operation.")

        if new_name is None:
            new_name = f"({other_solid.name}_{name_joiner}_{self.name})"
        new_solid = BooleanSolid(name=new_name)
        new_solid.g4_solid = new_g4_solid
        new_solid.creator_solid_1(other_solid)
        new_solid.creator_solid_2(self)
        return new_solid


class BoxSolid(BooleanSolid):
    user_info_defaults = {}
    user_info_defaults["size"] = (
        [10 * g4_units("cm"), 10 * g4_units("cm"), 10 * g4_units("cm")],
        {"doc": "3 component list of side lengths of the box."},
    )

    def build_solid(self):
        return g4.G4Box(
            self.name, self.size[0] / 2.0, self.size[1] / 2.0, self.size[2] / 2.0
        )


class HexagonSolid(BooleanSolid):
    """
    This is the special case of a six-sided polyhedron.
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {}
    user_info_defaults["height"] = (
        5 * g4_units("cm"),
        {"doc": "Height of the hexagon volume."},
    )
    user_info_defaults["radius"] = (
        0.15 * g4_units("cm"),
        {"doc": "Radius from the center to corners."},
    )

    def build_solid(self):
        deg = g4_units("deg")
        phi_start = 0 * deg
        phi_total = 360 * deg
        num_side = 6
        num_zplanes = 2
        zplane = [-self.height / 2, self.height / 2]
        radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        radius_outer = [self.radius] * num_side

        return g4.G4Polyhedra(
            self.name,
            phi_start,
            phi_total,
            num_side,
            num_zplanes,
            zplane,
            radius_inner,
            radius_outer,
        )


class ConsSolid(BooleanSolid):
    """Cone section.
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {}
    user_info_defaults["rmin1"] = (
        5 * g4_units("mm"),
        {"doc": "Inner radius at the lower end."},
    )
    user_info_defaults["rmin2"] = (
        20 * g4_units("mm"),
        {"doc": "Inner radius at the upper end."},
    )
    user_info_defaults["rmax1"] = (
        10 * g4_units("mm"),
        {"doc": "Outer radius at the lower end."},
    )
    user_info_defaults["rmax2"] = (
        25 * g4_units("mm"),
        {"doc": "Outer radius at the upper end."},
    )
    user_info_defaults["dz"] = (40 * g4_units("mm"), {"doc": "Half length in Z."})
    user_info_defaults["sphi"] = (
        0 * g4_units("deg"),
        {"doc": "Starting angle of the segment in radians."},
    )
    user_info_defaults["dphi"] = (
        45 * g4_units("deg"),
        {"doc": "The angle of the segment in radians."},
    )

    def build_solid(self):
        return g4.G4Cons(
            self.name,
            self.rmin1,
            self.rmax1,
            self.rmin2,
            self.rmax2,
            self.dz,
            self.sphi,
            self.dphi,
        )


class PolyhedraSolid(BooleanSolid):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {}
    user_info_defaults["phi_start"] = (
        0 * g4_units("deg"),
        {"doc": "Initial Phi starting angle"},
    )
    user_info_defaults["phi_total"] = (
        360 * g4_units("deg"),
        {"doc": "Total Phi angle"},
    )
    user_info_defaults["num_side"] = (6, {"doc": "Number of sides."})
    user_info_defaults["num_zplanes"] = (2, {"doc": "Number Z planes."})
    user_info_defaults["zplane"] = (
        [-2.5 * g4_units("cm"), 2.5 * g4_units("cm")],
        {"doc": "Position of Z planes. Should be a list with one position per plane."},
    )
    user_info_defaults["radius_inner"] = (
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        {
            "doc": "Tangent distance to inner surface. Should be a list with one distance per side."
        },
    )
    user_info_defaults["radius_outer"] = (
        [0.15 * g4_units("cm")] * 6,
        {
            "doc": "Tangent distance to outer surface. Should be a list with one distance per side."
        },
    )

    def build_solid(self):
        return g4.G4Polyhedra(
            self.name,
            self.phi_start,
            self.phi_total,
            self.num_side,
            self.num_zplanes,
            self.zplane,
            self.radius_inner,
            self.radius_outer,
        )


class SphereSolid(BooleanSolid):
    user_info_defaults = {}
    user_info_defaults["rmin"] = (0, {"doc": "Inner radius (0 means solid sphere)."})
    user_info_defaults["rmax"] = (
        1 * g4_units("mm"),
        {"doc": "Outer radius of the sphere."},
    )
    user_info_defaults["sphi"] = (0, {"doc": ""})
    user_info_defaults["dphi"] = (180 * g4_units("deg"), {"doc": ""})
    user_info_defaults["stheta"] = (0, {"doc": ""})
    user_info_defaults["dtheta"] = (180 * g4_units("deg"), {"doc": ""})

    def build_solid(self):
        return g4.G4Sphere(
            self.name,
            self.rmin,
            self.rmax,
            self.sphi,
            self.dphi,
            self.stheta,
            self.dtheta,
        )


class TrapSolid(BooleanSolid):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {}
    user_info_defaults["dx1"] = (
        30 * g4_units("mm"),
        {"doc": "Half x length of the side at y=-pdy1 of the face at -pdz"},
    )
    user_info_defaults["dx2"] = (
        40 * g4_units("mm"),
        {"doc": "Half x length of the side at y=+pdy1 of the face at -pdz"},
    )
    user_info_defaults["dy1"] = (40 * g4_units("mm"), {"doc": "Half y length at -pdz"})
    user_info_defaults["dy2"] = (16 * g4_units("mm"), {"doc": "Half y length at +pdz"})
    user_info_defaults["dx3"] = (
        10 * g4_units("mm"),
        {"doc": "Half x length of the side at y=-pdy2 of the face at +pdz"},
    )
    user_info_defaults["dx4"] = (
        14 * g4_units("mm"),
        {"doc": "Half x length of the side at y=+pdy2 of the face at +pdz"},
    )
    user_info_defaults["dz"] = (60 * g4_units("mm"), {"doc": "Half z length"})
    user_info_defaults["theta"] = (
        20 * g4_units("deg"),
        {"doc": "Polar angle of the line joining the centres of the faces at -/+pdz"},
    )
    user_info_defaults["phi"] = (
        5 * g4_units("deg"),
        {
            "doc": "Azimuthal angle of the line joining the centre of the face at -pdz to the centre of the face at +pdz"
        },
    )
    user_info_defaults["alp1"] = (
        10 * g4_units("deg"),
        {
            "doc": "Angle with respect to the y axis from the centre of the side (lower endcap)"
        },
    )
    user_info_defaults["alp2"] = (
        10 * g4_units("deg"),
        {
            "doc": "Angle with respect to the y axis from the centre of the side (upper endcap)"
        },
    )

    def build_solid(self):
        return g4.G4Trap(
            self.name,
            self.dz,
            self.theta,
            self.phi,
            self.dy1,
            self.dx1,
            self.dx2,
            self.alp1,
            self.dy2,
            self.dx3,
            self.dx4,
            self.alp2,
        )


class TrdSolid(BooleanSolid):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html?highlight=g4trd

    dx1 Half-length along X at the surface positioned at -dz
    dx2 Half-length along X at the surface positioned at +dz
    dy1 Half-length along Y at the surface positioned at -dz
    dy2 Half-length along Y at the surface positioned at +dz
    zdz Half-length along Z axis

    """

    user_info_defaults = {}
    user_info_defaults["dx1"] = (
        30 * g4_units("mm"),
        {"doc": "Half-length along X at the surface positioned at -dz"},
    )
    user_info_defaults["dx2"] = (
        10 * g4_units("mm"),
        {"doc": "dx2 Half-length along X at the surface positioned at +dz"},
    )
    user_info_defaults["dy1"] = (
        40 * g4_units("mm"),
        {"doc": "dy1 Half-length along Y at the surface positioned at -dz"},
    )
    user_info_defaults["dy2"] = (
        15 * g4_units("mm"),
        {"doc": "dy2 Half-length along Y at the surface positioned at +dz"},
    )
    user_info_defaults["dz"] = (
        15 * g4_units("mm"),
        {"doc": "Half-length along Z axis"},
    )

    def build_solid(self):
        return g4.G4Trd(self.name, self.dx1, self.dx2, self.dy1, self.dy2, self.dz)


class TubsSolid(BooleanSolid):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {}
    user_info_defaults["rmin"] = (30 * g4_units("mm"), {"doc": "Inner radius"})
    user_info_defaults["rmax"] = (40 * g4_units("mm"), {"doc": "Outer radius"})
    user_info_defaults["dz"] = (40 * g4_units("mm"), {"doc": "Half length along Z"})
    user_info_defaults["sphi"] = (0 * g4_units("deg"), {"doc": "Start angle phi"})
    user_info_defaults["dphi"] = (360 * g4_units("deg"), {"doc": "Angle segment"})

    def build_solid(self):
        return g4.G4Tubs(self.name, self.rmin, self.rmax, self.dz, self.sphi, self.dphi)


# solid_classes = [BooleanSolid, BoxSolid, HexagonSolid, ConsSolid, PolyhedraSolid, \
#                  SphereSolid, TrapSolid, TrdSolid, TubsSolid]
