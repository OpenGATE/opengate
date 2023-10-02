import opengate as gate
import opengate_core as g4
import stl

# import pybind11


class TesselatedVolume(gate.VolumeBase):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html?highlight=tesselated#tessellated-solids
    """

    type_name = "Tesselated"

    def __init__(self, user_info):
        super().__init__(user_info)
        self.facetArray = None
        # self.tessellated_solid = None
        # self.box_mesh = None

    @staticmethod
    def set_default_user_info(user_info):
        gate.VolumeBase.set_default_user_info(user_info)
        u = user_info
        mm = gate.g4_units("mm")
        u.file_name = ""
        u.unit = mm

    def read_file(self):
        try:
            u = self.user_info
            box_mesh = stl.mesh.Mesh.from_file(u.file_name)
        except Exception as e:
            print(
                "Error in TesselatedVolume. Could not read the file ",
                u.file_name,
                " Aborting.",
            )
            print("The error encountered was: ", e)
            exit()
        return box_mesh

    def translate_mesh_to_center(self, mesh_to_translate):
        # translate the mesh to the center of gravity
        cog = mesh_to_translate.get_mass_properties()[1]
        mesh_to_translate.translate(-cog)
        return mesh_to_translate

    def build_solid(self):
        u = self.user_info
        box_mesh = self.read_file()
        # translate the mesh to the center of gravity
        box_mesh = self.translate_mesh_to_center(box_mesh)
        # print("box_mesh: ", self.box_mesh)

        # generate the tessellated solid
        tessellated_solid = g4.G4TessellatedSolid(u.name)

        # create an array of facets
        self.facetArray = []
        for vertex in box_mesh.vectors:
            # Create the new facet
            # ABSOLUTE =0
            # RELATIVE =1
            g4Facet = g4.G4TriangularFacet(
                gate.vec_np_as_g4(vertex[0]),
                gate.vec_np_as_g4(vertex[1]),
                gate.vec_np_as_g4(vertex[2]),
                g4.G4FacetVertexType.ABSOLUTE,
            )
            self.facetArray.append(g4Facet)
        print("facetArray: ", self.facetArray)

        # loop through facetArray and add the facets to the tessellated solid
        for facet in self.facetArray:
            # print("g4Facet: ", facet)
            tessellated_solid.AddFacet(facet)
            # print("tessellated_solid ", tessellated_solid)

        # print("finished creating solid")
        # set the solid closed
        tessellated_solid.SetSolidClosed(True)
        # print("end of tesselated solid: ", self.tessellated_solid)

        return tessellated_solid
