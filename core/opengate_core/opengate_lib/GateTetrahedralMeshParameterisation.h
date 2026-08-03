/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTetrahedralMeshParameterisation_h
#define GateTetrahedralMeshParameterisation_h

#include <map>
#include <string>
#include <unordered_map>
#include <vector>

#include "G4Colour.hh"
#include "G4VNestedParameterisation.hh"
#include "globals.hh"

class G4LogicalVolume;
class G4Material;
class G4Tet;
class G4VisAttributes;
class G4VPhysicalVolume;
class G4VSolid;

class GateTetrahedralMeshParameterisation
    : public G4VNestedParameterisation {
 public:
  GateTetrahedralMeshParameterisation(
      std::vector<G4Tet *> solids,
      std::vector<G4Material *> unique_materials,
      std::vector<unsigned int> material_index_per_copy,
      std::vector<int> region_per_copy,
      std::unordered_map<int, G4Colour> region_to_colour,
      std::unordered_map<int, bool> region_visible);

  ~GateTetrahedralMeshParameterisation() override = default;

  void ComputeTransformation(
      G4int copy_number, G4VPhysicalVolume *physical_volume) const override;

  G4Material *ComputeMaterial(
      G4VPhysicalVolume *current_volume,
      G4int copy_number,
      const G4VTouchable *parent_touch = nullptr) override;

  G4VSolid *ComputeSolid(
      G4int copy_number, G4VPhysicalVolume *physical_volume) override;

  G4int GetNumberOfMaterials() const override;

  G4Material *GetMaterial(G4int index) const override;

 private:
  G4VisAttributes *get_or_create_vis(int region);

  std::vector<G4Tet *> fSolids;
  std::vector<G4Material *> fUniqueMaterials;
  std::vector<unsigned int> fMaterialIndexPerCopy;
  std::vector<int> fRegionPerCopy;
  std::unordered_map<int, G4Colour> fRegionToColour;
  std::unordered_map<int, bool> fRegionVisible;
  std::unordered_map<int, G4VisAttributes *> fVisCache;
};

G4VPhysicalVolume *build_tetrahedral_mesh_from_tetgen(
    const std::string &node_path,
    const std::string &ele_path,
    G4LogicalVolume *mother_lv,
    const std::map<int, G4Material *> &region_to_material,
    const std::unordered_map<int, G4Colour> &region_to_colour,
    const std::unordered_map<int, bool> &region_visible,
    G4Material *default_material,
    const std::string &pv_name,
    G4bool check_overlaps,
    G4double scale);

G4VPhysicalVolume *build_mrcp_tetrahedral_mesh_from_tetgen(
    const std::string &node_path,
    const std::string &ele_path,
    G4LogicalVolume *mother_lv,
    const std::map<int, G4Material *> &region_to_material,
    const std::unordered_map<int, G4Colour> &region_to_colour,
    const std::unordered_map<int, bool> &region_visible,
    G4Material *default_material,
    const std::string &pv_name,
    G4bool check_overlaps);

G4VPhysicalVolume *build_tetrahedral_mesh_from_tetgen_material_names(
    G4LogicalVolume *mother_lv,
    const std::string &pv_name,
    const std::string &node_path,
    const std::string &ele_path,
    const std::map<int, std::string> &region_id_to_mat_name,
    G4double scale,
    G4bool check_overlaps);

#endif // GateTetrahedralMeshParameterisation_h
