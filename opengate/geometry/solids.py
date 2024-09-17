from box import Box
from scipy.spatial.transform import Rotation
import stl
import logging

from ..base import GateObject, process_cls, create_gate_object_from_dict
from ..utility import g4_units
from ..exception import fatal
import opengate_core as g4
from ..decorators import requires_fatal

from .utility import ensure_is_g4_rotation, ensure_is_g4_translation, vec_np_as_g4


logger = logging.getLogger(__name__)


class SolidBase(GateObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.g4_solid = None

    def close(self):
        self.release_g4_references()
        super().close()

    def release_g4_references(self):
        self.g4_solid = None

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_solid"] = None
        return return_dict

    @property
    def solid_info(self):
        """Computes the properties of the solid associated with this volume."""
        # Note: This method only works in derived classes which implement the build_solid method.
        solid = self.build_solid()
        if solid is None:
            fatal(
                f"Cannot compute solid info for this volume {self.name}. Unable to build the solid."
            )
        r = Box()
        r.cubic_volume = solid.GetCubicVolume()
        r.surface_area = solid.GetSurfaceArea()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        solid.BoundingLimits(pMin, pMax)
        r.bounding_limits = [pMin, pMax]
        return r

    @property
    def bounding_limits(self):
        """
        Return the min and max 3D points of the bounding box of the given volume
        """
        pMin, pMax = self.solid_info.bounding_limits
        return pMin, pMax

    @property
    def bounding_box_size(self):
        """
        Return the size of the bounding box of the given volume
        """
        pMin, pMax = self.bounding_limits
        return [pMax[0] - pMin[0], pMax[1] - pMin[1], pMax[2] - pMin[2]]

    # The construct_solid method is implemented here, but will only work with objects
    # of the derived classes which implement the build_solid method,
    # or which override the construct_solid method
    def construct_solid(self):
        """Attempts to build the solid according the build_solid() method either coming from a Solid mother class
        or implemented in a specific derived class.
        """
        # The solid can only be constructed once
        if self.g4_solid is None:
            self.g4_solid = self.build_solid()


class BooleanSolid(SolidBase):
    constructor_functions = {
        "intersect": g4.G4IntersectionSolid,
        "add": g4.G4UnionSolid,
        "subtract": g4.G4SubtractionSolid,
    }

    user_info_defaults = {
        "creator_volumes": (
            [None, None],
            {
                "doc": "A tuple of the two volumes which were combined by boolean operation to create this volume. "
                "This user info is set internally when applying a boolean operation "
                "and cannot be set by the user. ",
                "read_only": True,
            },
        ),
        "operation": ("none", {"doc": "FIXME"}),
        "rotation_boolean_operation": (
            Rotation.identity().as_matrix(),
            {"doc": "FIXME"},
        ),
        "translation_boolean_operation": ([0, 0, 0], {"doc": "FIXME"}),
    }

    def build_solid(self):
        """Overrides the method from the base class.
        It constructs the solid according to the logic of the G4 boolean volumes.
        """
        g4_rotation = ensure_is_g4_rotation(self.rotation_boolean_operation)
        g4_translation = ensure_is_g4_translation(self.translation_boolean_operation)

        # make sure creator volumes have their solids constructed
        for cv in self.creator_volumes:
            cv.construct_solid()

        return self.constructor_functions[self.operation](
            self.name,
            self.creator_volumes[0].g4_solid,
            self.creator_volumes[1].g4_solid,
            g4_rotation,
            g4_translation,
        )

    def from_dictionary(self, d):
        super().from_dictionary(d)
        try:
            creator_volumes = d["user_info"]["creator_volumes"]
        except KeyError:
            fatal(
                f"Error while populating object named {self.name}: "
                "The provided dictionary does not contain an entry 'creator_volumes'."
            )
        for i, cv in enumerate(creator_volumes):
            try:
                vol = self.volume_manager.volumes[cv["user_info"]["name"]]
            except KeyError:
                vol = create_gate_object_from_dict(cv)

            self.creator_volumes[i] = vol
            self.creator_volumes[i].from_dictionary(cv)


class BoxSolid(SolidBase):
    user_info_defaults = {
        "size": (
            [10 * g4_units.cm, 10 * g4_units.cm, 10 * g4_units.cm],
            {"doc": "3 component list of side lengths of the box."},
        )
    }

    def build_solid(self):
        return g4.G4Box(
            self.name, self.size[0] / 2.0, self.size[1] / 2.0, self.size[2] / 2.0
        )


class HexagonSolid(SolidBase):
    """
    This is the special case of a six-sided polyhedron.
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {
        "height": (
            5 * g4_units.cm,
            {"doc": "Height of the hexagon volume."},
        ),
        "radius": (
            0.15 * g4_units.cm,
            {"doc": "Radius from the center to corners."},
        ),
    }

    def build_solid(self):
        deg = g4_units.deg
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


class ConsSolid(SolidBase):
    """Cone section.
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {
        "rmin1": (
            5 * g4_units.mm,
            {"doc": "Inner radius at the lower end."},
        ),
        "rmin2": (
            20 * g4_units.mm,
            {"doc": "Inner radius at the upper end."},
        ),
        "rmax1": (
            10 * g4_units.mm,
            {"doc": "Outer radius at the lower end."},
        ),
        "rmax2": (
            25 * g4_units.mm,
            {"doc": "Outer radius at the upper end."},
        ),
        "dz": (40 * g4_units.mm, {"doc": "Half length in Z."}),
        "sphi": (
            0 * g4_units.deg,
            {"doc": "Starting angle of the segment in radians."},
        ),
        "dphi": (
            45 * g4_units.deg,
            {"doc": "The angle of the segment in radians."},
        ),
    }

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


class PolyhedraSolid(SolidBase):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {
        "phi_start": (
            0 * g4_units.deg,
            {"doc": "Initial Phi starting angle"},
        ),
        "phi_total": (
            360 * g4_units.deg,
            {"doc": "Total Phi angle"},
        ),
        "num_side": (6, {"doc": "Number of sides."}),
        "num_zplanes": (2, {"doc": "Number Z planes."}),
        "zplane": (
            [-2.5 * g4_units.cm, 2.5 * g4_units.cm],
            {
                "doc": "Position of Z planes. Should be a list with one position per plane."
            },
        ),
        "radius_inner": (
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            {
                "doc": "Tangent distance to inner surface. Should be a list with one distance per side."
            },
        ),
        "radius_outer": (
            [0.15 * g4_units.cm] * 6,
            {
                "doc": "Tangent distance to outer surface. Should be a list with one distance per side."
            },
        ),
    }

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


class SphereSolid(SolidBase):
    user_info_defaults = {
        "rmin": (0, {"doc": "Inner radius (0 means solid sphere)."}),
        "rmax": (
            1 * g4_units.mm,
            {"doc": "Outer radius of the sphere."},
        ),
        "sphi": (0, {"doc": ""}),
        "dphi": (
            360 * g4_units.deg,
            {"doc": "Angular size of the sphere section around the rotation axis. "},
        ),
        "stheta": (0, {"doc": ""}),
        "dtheta": (180 * g4_units.deg, {"doc": ""}),
    }

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


class TrapSolid(SolidBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {
        "dx1": (
            30 * g4_units.mm,
            {"doc": "Half x length of the side at y=-pdy1 of the face at -pdz"},
        ),
        "dx2": (
            40 * g4_units.mm,
            {"doc": "Half x length of the side at y=+pdy1 of the face at -pdz"},
        ),
        "dy1": (40 * g4_units.mm, {"doc": "Half y length at -pdz"}),
        "dy2": (16 * g4_units.mm, {"doc": "Half y length at +pdz"}),
        "dx3": (
            10 * g4_units.mm,
            {"doc": "Half x length of the side at y=-pdy2 of the face at +pdz"},
        ),
        "dx4": (
            14 * g4_units.mm,
            {"doc": "Half x length of the side at y=+pdy2 of the face at +pdz"},
        ),
        "dz": (60 * g4_units.mm, {"doc": "Half z length"}),
        "theta": (
            20 * g4_units.deg,
            {
                "doc": "Polar angle of the line joining the centres of the faces at -/+pdz"
            },
        ),
        "phi": (
            5 * g4_units.deg,
            {
                "doc": "Azimuthal angle of the line joining the centre of the face at -pdz "
                "to the centre of the face at +pdz"
            },
        ),
        "alp1": (
            10 * g4_units.deg,
            {
                "doc": "Angle with respect to the y axis from the centre of the side (lower endcap)"
            },
        ),
        "alp2": (
            10 * g4_units.deg,
            {
                "doc": "Angle with respect to the y axis from the centre of the side (upper endcap)"
            },
        ),
    }

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


class TrdSolid(SolidBase):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html?highlight=g4trd

    dx1 Half-length along X at the surface positioned at -dz
    dx2 Half-length along X at the surface positioned at +dz
    dy1 Half-length along Y at the surface positioned at -dz
    dy2 Half-length along Y at the surface positioned at +dz
    zdz Half-length along Z axis

    """

    user_info_defaults = {
        "dx1": (
            30 * g4_units.mm,
            {"doc": "Half-length along X at the surface positioned at -dz"},
        ),
        "dx2": (
            10 * g4_units.mm,
            {"doc": "dx2 Half-length along X at the surface positioned at +dz"},
        ),
        "dy1": (
            40 * g4_units.mm,
            {"doc": "dy1 Half-length along Y at the surface positioned at -dz"},
        ),
        "dy2": (
            15 * g4_units.mm,
            {"doc": "dy2 Half-length along Y at the surface positioned at +dz"},
        ),
        "dz": (
            15 * g4_units.mm,
            {"doc": "Half-length along Z axis"},
        ),
    }

    def build_solid(self):
        return g4.G4Trd(self.name, self.dx1, self.dx2, self.dy1, self.dy2, self.dz)


class TubsSolid(SolidBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html

    """

    user_info_defaults = {
        "rmin": (30 * g4_units.mm, {"doc": "Inner radius"}),
        "rmax": (40 * g4_units.mm, {"doc": "Outer radius"}),
        "dz": (40 * g4_units.mm, {"doc": "Half length along Z"}),
        "sphi": (0 * g4_units.deg, {"doc": "Start angle phi"}),
        "dphi": (360 * g4_units.deg, {"doc": "Angle segment"}),
    }

    def build_solid(self):
        return g4.G4Tubs(self.name, self.rmin, self.rmax, self.dz, self.sphi, self.dphi)


class TesselatedSolid(SolidBase):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html?highlight=tesselated#tessellated-solids
    """

    user_info_defaults = {
        "file_name": ("", {"doc": "Path and file name of the STL file."}),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.g4_facets = None

    def close(self):
        # G4Facets are deleted by the destructor of G4TesselatedSolid,
        # so we need to release the reference to it on the python side.
        # self.g4_facets = None
        super().close()

    def read_file(self):
        try:
            return stl.mesh.Mesh.from_file(self.file_name)
        except Exception as e:
            msg = (
                f"Error in {self.type_name} called {self.name}. Could not read the file {self.file_name}. Aborting. "
                f"The error encountered was: \n{e}"
            )
            fatal(msg)

    def translate_mesh_to_center(self, mesh_to_translate):
        # translate the mesh to the center of gravity
        cog = mesh_to_translate.get_mass_properties()[1]
        mesh_to_translate.translate(-cog)
        return mesh_to_translate

    def build_solid(self):
        mm = g4_units.mm
        # translate the mesh to the center of gravity
        box_mesh = self.translate_mesh_to_center(self.read_file())
        # generate the tessellated solid
        tessellated_solid = g4.G4TessellatedSolid(self.name)
        # create an array of facets
        # self.g4_facets = []
        for vertex in box_mesh.vectors:
            # Create the new facet
            # ABSOLUTE =0
            # RELATIVE =1
            g4_facet = g4.G4TriangularFacet(
                vec_np_as_g4(vertex[0]),
                vec_np_as_g4(vertex[1]),
                vec_np_as_g4(vertex[2]),
                g4.G4FacetVertexType.ABSOLUTE,
            )
            tessellated_solid.AddFacet(g4_facet)
            # self.g4_facets.append(g4_facet)

        # set the solid closed
        tessellated_solid.SetSolidClosed(True)
        logger.debug(
            f"Created tesselated volume '{self.name}' with a volume of {tessellated_solid.GetCubicVolume() / mm**3} mm3"
        )

        return tessellated_solid


class ImageSolid(SolidBase):
    """Utility to handle the solids of an ImageVolume.
    It is not intended to be used stand-alone, but only as a base class of ImageVolume.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These parameters are NOT user infos
        # They are derived from the ITK image in the ImageVolume class
        self.half_size_mm = None
        self.half_spacing = None

        self.g4_solid_x = None
        self.g4_solid_y = None
        self.g4_solid_z = None

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_solid_x"] = None
        return_dict["g4_solid_y"] = None
        return_dict["g4_solid_z"] = None
        return return_dict

    def close(self):
        self.release_g4_references()
        super().close()

    def release_g4_references(self):
        self.g4_solid_x = None
        self.g4_solid_y = None
        self.g4_solid_z = None

    @requires_fatal("half_size_mm")
    @requires_fatal("half_spacing")
    def construct_solid(self):
        self.g4_solid_x = g4.G4Box(
            self.name + "_X",
            self.half_spacing[0],
            self.half_spacing[1],
            self.half_size_mm[2],
        )
        self.g4_solid_y = g4.G4Box(
            self.name + "_Y",
            self.half_size_mm[0],
            self.half_spacing[1],
            self.half_size_mm[2],
        )
        self.g4_solid_z = g4.G4Box(
            self.name + "_Z",
            self.half_spacing[0],
            self.half_spacing[1],
            self.half_spacing[2],
        )
        self.g4_solid = g4.G4Box(
            self.name, self.half_size_mm[0], self.half_size_mm[1], self.half_size_mm[2]
        )


process_cls(SolidBase)
process_cls(BooleanSolid)
process_cls(BoxSolid)
process_cls(HexagonSolid)
process_cls(ConsSolid)
process_cls(PolyhedraSolid)
process_cls(SphereSolid)
process_cls(TrapSolid)
process_cls(TrdSolid)
process_cls(TubsSolid)
process_cls(ImageSolid)
process_cls(TesselatedSolid)
