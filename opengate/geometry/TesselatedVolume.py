import opengate as gate
import opengate_core as g4
import stl
import pybind11


class TesselatedVolume(gate.VolumeBase):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html?highlight=tesselated#tessellated-solids
    """

    type_name = "Tesselated"

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
        mm = gate.g4_units("mm")

        u = self.user_info
        box_mesh = self.read_file()
        # translate the mesh to the center of gravity
        box_mesh = self.translate_mesh_to_center(box_mesh)
        print("box_mesh: ", box_mesh)

        # generate the tessellated solid
        tessellated_solid = g4.G4TessellatedSolid(u.name)

        # create an array of facets
        facetArray = []
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
            facetArray.append(g4Facet)
        print("facetArray: ", facetArray)

        # loop through facetArray and add the facets to the tessellated solid
        for facet in facetArray:
            print("g4Facet: ", facet)
            tessellated_solid.AddFacet(facet)
            # print("tessellated_solid ", tessellated_solid)

        print("finished creating solid")
        # set the solid closed
        tessellated_solid.SetSolidClosed(True)
        print("end of tesselated solid: ", tessellated_solid)

        # # loop through the facets of the mesh and add them to the tessellated solid
        # for vertex in box_mesh.vectors:
        #     # Create the new facet
        #     # ABSOLUTE =0
        #     # RELATIVE =1

        #     g4Facet = g4.G4TriangularFacet(
        #         gate.vec_np_as_g4(vertex[0]),
        #         gate.vec_np_as_g4(vertex[1]),
        #         gate.vec_np_as_g4(vertex[2]),
        #         g4.G4FacetVertexType.ABSOLUTE,
        #     )

        #     # Pass the G4TesselatedSolid object to the C++ function using a shared_ptr
        #     shared_ptr = g4.std_make_shared_G4TesselatedSolid(tessellated_solid)
        #     # add facet
        #     # tessellated_solid.AddFacet(g4Facet)
        #     tessellated_solid.AddFacet(shared_ptr)

        #     # print("vertex: ", vertex[0], vertex[1], vertex[2])
        #     # print(
        #     #     "vertex as g4Vector ",
        #     #     gate.vec_np_as_g4(vertex[0] * mm),
        #     #     gate.vec_np_as_g4(vertex[1] * mm),
        #     #     gate.vec_np_as_g4(vertex[2] * mm),
        #     # )
        #     # print("g4Facet: ", g4Facet)
        #     # # Add the facet to the tessellated solid
        #     # tessellated_solid.AddFacet(g4Facet)
        #     # print("tessellated_solid ", tessellated_solid)
        # tessellated_solid.SetSolidClosed(True)
        # print("end of tesselated solid: ", tessellated_solid)

        return tessellated_solid
