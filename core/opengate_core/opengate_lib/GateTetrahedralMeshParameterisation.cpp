/* --------------------------------------------------
   G4Tet-based tetrahedral mesh implementation for OpenGATE
   - Builds ONE parameterised volume (G4PVParameterised + G4VNestedParameterisation)
   - IMPORTANT (GeomVol0002): the parameterised PV MUST be the ONLY daughter of mother_lv.
   -------------------------------------------------- */

#include "GateTetrahedralMeshParameterisation.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include <map>
#include <limits>

#include "globals.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVParameterised.hh"
#include "G4Colour.hh"
#include "G4SystemOfUnits.hh"
#include "G4Tet.hh"
#include "G4Threading.hh"
#include "G4ThreeVector.hh"
#include "G4VNestedParameterisation.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VTouchable.hh"
#include "G4VisAttributes.hh"

// --------------------------------------------------------------------------------------
// TetGen .node/.ele parsing
// --------------------------------------------------------------------------------------

struct NodeRec {
  G4double x{0}, y{0}, z{0};
};

struct NodeTable {
  std::vector<NodeRec> nodes;  // stored 0..N-1
  int index_base{1};           // 0 if input uses 0-based IDs, 1 if input uses 1-based IDs
  int n_points{0};
};

struct EleRec {
  int id{0};
  int n1{0}, n2{0}, n3{0}, n4{0};
  int region{0};  // first attribute interpreted as region/material id (if present)
};

static inline std::string strip_comment(const std::string &line) {
  auto pos = line.find('#');
  return (pos == std::string::npos) ? line : line.substr(0, pos);
}

static inline bool is_blank(const std::string &s) {
  for (char c : s) {
    if (!std::isspace(static_cast<unsigned char>(c))) return false;
  }
  return true;
}


static NodeTable read_node_file(const std::string &path,
                                G4double input_length_unit) {
  std::ifstream fin(path);
  if (!fin) throw std::runtime_error("Cannot open .node file: " + path);

  std::string line;
  int n_points = 0, dim = 0, n_attr = 0, has_bm = 0;

  // Header: <#points> <dim> <#attr> <#bm>
  while (std::getline(fin, line)) {
    line = strip_comment(line);
    if (is_blank(line)) continue;
    std::istringstream iss(line);
    if (!(iss >> n_points >> dim >> n_attr >> has_bm))
      throw std::runtime_error("Invalid .node header in: " + path);
    break;
  }
  if (n_points <= 0 || dim < 3)
    throw std::runtime_error("Unexpected .node header values in: " + path);

  std::vector<NodeRec> nodes(static_cast<size_t>(n_points));  // stored 0..N-1
  int read_count = 0;
  int min_idx = std::numeric_limits<int>::max();
  int max_idx = std::numeric_limits<int>::min();

  // Read node lines: <idx> <x> <y> <z> ...
  // We accept either 0-based (0..N-1) or 1-based (1..N) indices.
  while (std::getline(fin, line)) {
    line = strip_comment(line);
    if (is_blank(line)) continue;
    std::istringstream iss(line);
    int idx = 0;
    G4double x = 0, y = 0, z = 0;
    if (!(iss >> idx >> x >> y >> z)) continue;

    min_idx = std::min(min_idx, idx);
    max_idx = std::max(max_idx, idx);

    // We'll temporarily store using a 0-based slot; decide base after first pass heuristics.
    // For now, store only if idx is in a plausible range for either convention.
    if (0 <= idx && idx < n_points) {
      nodes[static_cast<size_t>(idx)] =
          NodeRec{x * input_length_unit, y * input_length_unit,
                  z * input_length_unit};
      read_count++;
    } else if (1 <= idx && idx <= n_points) {
      nodes[static_cast<size_t>(idx - 1)] =
          NodeRec{x * input_length_unit, y * input_length_unit,
                  z * input_length_unit};
      read_count++;
    }
  }

  if (read_count == 0)
    throw std::runtime_error("No nodes were read from: " + path);

  NodeTable t;
  t.nodes = std::move(nodes);
  t.n_points = n_points;

  // Determine index base from observed min/max.
  // Typical TetGen: either 0..N-1 or 1..N.
  if (min_idx == 0 && max_idx == n_points - 1) {
    t.index_base = 0;
  } else if (min_idx == 1 && max_idx == n_points) {
    t.index_base = 1;
  } else {
    // Mixed or unusual; pick base by whether 0 appears.
    t.index_base = (min_idx == 0) ? 0 : 1;
  }

  return t;
}

static std::vector<EleRec> read_ele_file(const std::string &path) {
  std::ifstream fin(path);
  if (!fin) throw std::runtime_error("Cannot open .ele file: " + path);

  std::string line;
  int n_tets = 0, nodes_per_tet = 0, n_attr = 0;

  while (std::getline(fin, line)) {
    line = strip_comment(line);
    if (is_blank(line)) continue;
    std::istringstream iss(line);
    if (!(iss >> n_tets >> nodes_per_tet >> n_attr))
      throw std::runtime_error("Invalid .ele header in: " + path);
    break;
  }
  if (n_tets <= 0 || nodes_per_tet != 4)
    throw std::runtime_error("Unexpected .ele header values in: " + path);

  std::vector<EleRec> tets;
  tets.reserve(static_cast<size_t>(n_tets));

  while (std::getline(fin, line)) {
    line = strip_comment(line);
    if (is_blank(line)) continue;
    std::istringstream iss(line);
    EleRec e{};
    if (!(iss >> e.id >> e.n1 >> e.n2 >> e.n3 >> e.n4)) continue;

    if (n_attr > 0) {
      double first_attr = 0.0;
      if (iss >> first_attr) e.region = static_cast<int>(first_attr);
    }
    tets.push_back(e);
  }

  if (tets.empty())
    throw std::runtime_error("No tetrahedra were read from: " + path);

  return tets;
}

// --------------------------------------------------------------------------------------
// Nested parameterisation
// --------------------------------------------------------------------------------------

GateTetrahedralMeshParameterisation::GateTetrahedralMeshParameterisation(
    std::vector<G4Tet *> solids,
    std::vector<G4Material *> unique_materials,
    std::vector<unsigned int> material_index_per_copy,
    std::vector<int> region_per_copy,
    std::unordered_map<int, G4Colour> region_to_colour,
    std::unordered_map<int, bool> region_visible)
    : fSolids(std::move(solids)),
      fUniqueMaterials(std::move(unique_materials)),
      fMaterialIndexPerCopy(std::move(material_index_per_copy)),
      fRegionPerCopy(std::move(region_per_copy)),
      fRegionToColour(std::move(region_to_colour)),
      fRegionVisible(std::move(region_visible)) {
  if (fSolids.empty())
    throw std::runtime_error(
        "GateTetrahedralMeshParameterisation: no solids");
  if (fUniqueMaterials.empty())
    throw std::runtime_error(
        "GateTetrahedralMeshParameterisation: no materials");
  if (fMaterialIndexPerCopy.size() != fSolids.size())
    throw std::runtime_error(
        "GateTetrahedralMeshParameterisation: material index size mismatch");
  if (fRegionPerCopy.size() != fSolids.size())
    throw std::runtime_error(
        "GateTetrahedralMeshParameterisation: region index size mismatch");
}

void GateTetrahedralMeshParameterisation::ComputeTransformation(
    G4int /*copy_number*/, G4VPhysicalVolume *physical_volume) const {
  physical_volume->SetTranslation(G4ThreeVector(0, 0, 0));
  physical_volume->SetRotation(nullptr);
}

G4Material *GateTetrahedralMeshParameterisation::ComputeMaterial(
    G4VPhysicalVolume *current_volume,
    G4int copy_number,
    const G4VTouchable *parent_touch) {
  const auto index =
      fMaterialIndexPerCopy.at(static_cast<size_t>(copy_number));
  auto *material = fUniqueMaterials.at(static_cast<size_t>(index));

  // Worker threads may navigate concurrently. Return the material there, but
  // only mutate the shared logical volume from the master thread.
  if (current_volume != nullptr && !G4Threading::IsWorkerThread()) {
    const auto region =
        fRegionPerCopy.at(static_cast<size_t>(copy_number));
    auto *logical_volume = current_volume->GetLogicalVolume();
    if (logical_volume != nullptr) {
      logical_volume->SetVisAttributes(get_or_create_vis(region));
      logical_volume->SetMaterial(material);
    }
  }
  (void)parent_touch;
  return material;
}

G4VSolid *GateTetrahedralMeshParameterisation::ComputeSolid(
    G4int copy_number, G4VPhysicalVolume * /*physical_volume*/) {
  return fSolids.at(static_cast<size_t>(copy_number));
}

G4int GateTetrahedralMeshParameterisation::GetNumberOfMaterials() const {
  return static_cast<G4int>(fUniqueMaterials.size());
}

G4Material *GateTetrahedralMeshParameterisation::GetMaterial(
    G4int index) const {
  return fUniqueMaterials.at(static_cast<size_t>(index));
}

G4VisAttributes *
GateTetrahedralMeshParameterisation::get_or_create_vis(int region) {
  auto existing = fVisCache.find(region);
  if (existing != fVisCache.end()) return existing->second;

  G4Colour colour(0.8, 0.8, 0.8, 1.0);
  auto configured_colour = fRegionToColour.find(region);
  if (configured_colour != fRegionToColour.end())
    colour = configured_colour->second;

  const bool visible =
      fRegionVisible.count(region) == 0 ? true : fRegionVisible.at(region);
  auto *attributes = new G4VisAttributes(colour);
  attributes->SetVisibility(visible);
  attributes->SetForceSolid(true);
  fVisCache.emplace(region, attributes);
  return attributes;
}

// Keep parameterisations alive for the whole run
static std::vector<std::unique_ptr<GateTetrahedralMeshParameterisation>>
    g_tetrahedral_mesh_parameterisations;

// --------------------------------------------------------------------------------------
// Forward declaration (avoids "undeclared identifier" errors)
// --------------------------------------------------------------------------------------
static G4VPhysicalVolume *build_tetrahedral_mesh_impl(const std::string &node_path,
                                                        const std::string &ele_path,
                                                        G4LogicalVolume *mother_lv,
                                                        const std::map<int, G4Material *> &region_to_material,
                                                        const std::unordered_map<int, G4Colour> &region_to_colour,
                                                        const std::unordered_map<int, bool> &region_visible,
                                                        G4Material *default_material,
                                                        const std::string &pv_name,
                                                        G4bool check_overlaps,
                                                        G4double node_coordinate_unit);

// --------------------------------------------------------------------------------------
// Material resolver for compat API
// --------------------------------------------------------------------------------------
static G4Material *resolve_material_by_name(const std::string &name) {
  if (name.empty()) return nullptr;
  if (auto *m = G4Material::GetMaterial(name, false)) return m;

  if (name.rfind("G4_", 0) == 0) {
    auto *nist = G4NistManager::Instance();
    if (auto *m = nist->FindOrBuildMaterial(name, false)) return m;
  }
  return nullptr;
}

// --------------------------------------------------------------------------------------
// New API wrapper (material pointers)
// --------------------------------------------------------------------------------------
G4VPhysicalVolume *build_tetrahedral_mesh_from_tetgen(const std::string &node_path,
                                               const std::string &ele_path,
                                               G4LogicalVolume *mother_lv,
                                               const std::map<int, G4Material *> &region_to_material,
                                               const std::unordered_map<int, G4Colour> &region_to_colour,
                                               const std::unordered_map<int, bool> &region_visible,
                                               G4Material *default_material,
                                               const std::string &pv_name,
                                               G4bool check_overlaps,
                                               G4double scale) {
  return build_tetrahedral_mesh_impl(node_path, ele_path, mother_lv, region_to_material,
                                       region_to_colour, region_visible,
                                       default_material, pv_name, check_overlaps,
                                       scale * mm);
}

// --------------------------------------------------------------------------------------
// MRCP API wrapper (MRCP .node coordinates are stored in centimetres)
// --------------------------------------------------------------------------------------
G4VPhysicalVolume *build_mrcp_tetrahedral_mesh_from_tetgen(
    const std::string &node_path,
    const std::string &ele_path,
    G4LogicalVolume *mother_lv,
    const std::map<int, G4Material *> &region_to_material,
    const std::unordered_map<int, G4Colour> &region_to_colour,
    const std::unordered_map<int, bool> &region_visible,
    G4Material *default_material,
    const std::string &pv_name,
    G4bool check_overlaps) {
  // Convert MRCP coordinates to Geant4 internal length units while parsing.
  return build_tetrahedral_mesh_impl(
      node_path, ele_path, mother_lv, region_to_material, region_to_colour,
      region_visible, default_material, pv_name, check_overlaps, cm);
}

// --------------------------------------------------------------------------------------
// Compat API wrapper (material names + scale, legacy argument order)
// --------------------------------------------------------------------------------------
G4VPhysicalVolume *build_tetrahedral_mesh_from_tetgen_material_names(
    G4LogicalVolume *mother_lv,
    const std::string &pv_name,
    const std::string &node_path,
    const std::string &ele_path,
    const std::map<int, std::string> &region_id_to_mat_name,
    G4double scale,
    G4bool check_overlaps) {

  std::map<int, G4Material *> region_to_material_ptr;
  for (const auto &kv : region_id_to_mat_name) {
    auto *m = resolve_material_by_name(kv.second);
    if (m != nullptr) region_to_material_ptr.emplace(kv.first, m);
  }

  return build_tetrahedral_mesh_impl(node_path, ele_path, mother_lv, region_to_material_ptr,
                                       /*region_to_colour=*/{}, /*region_visible=*/{},
                                       /*default_material=*/nullptr, pv_name,
                                       check_overlaps, scale * mm);
}

// --------------------------------------------------------------------------------------
// Internal implementation
// --------------------------------------------------------------------------------------
static G4VPhysicalVolume *build_tetrahedral_mesh_impl(const std::string &node_path,
                                                        const std::string &ele_path,
                                                        G4LogicalVolume *mother_lv,
                                                        const std::map<int, G4Material *> &region_to_material,
                                                        const std::unordered_map<int, G4Colour> &region_to_colour,
                                                        const std::unordered_map<int, bool> &region_visible,
                                                        G4Material *default_material,
                                                        const std::string &pv_name,
                                                        G4bool check_overlaps,
                                                        G4double node_coordinate_unit) {
  if (mother_lv == nullptr) throw std::runtime_error("mother_lv is null");

  if (default_material == nullptr) {
    default_material = G4NistManager::Instance()->FindOrBuildMaterial("G4_AIR");
    if (default_material == nullptr)
      throw std::runtime_error("Cannot build default material G4_AIR");
  }

  const auto node_table = read_node_file(node_path, node_coordinate_unit);
  const auto elems = read_ele_file(ele_path);

  // Keep tetrahedra centered inside the already-centered mother container LV.
  // The Python example translates the outer phantom volume by the global bbox
  // center, so the parameterised tets must be shifted by -center here, matching
  // the legacy per-tet placement builder behavior.
  G4double min_x = std::numeric_limits<G4double>::max();
  G4double min_y = std::numeric_limits<G4double>::max();
  G4double min_z = std::numeric_limits<G4double>::max();
  G4double max_x = std::numeric_limits<G4double>::lowest();
  G4double max_y = std::numeric_limits<G4double>::lowest();
  G4double max_z = std::numeric_limits<G4double>::lowest();
  for (const auto &n : node_table.nodes) {
    min_x = std::min(min_x, n.x);
    min_y = std::min(min_y, n.y);
    min_z = std::min(min_z, n.z);
    max_x = std::max(max_x, n.x);
    max_y = std::max(max_y, n.y);
    max_z = std::max(max_z, n.z);
  }
  const G4ThreeVector mesh_center(0.5 * (min_x + max_x),
                                  0.5 * (min_y + max_y),
                                  0.5 * (min_z + max_z));

  std::vector<G4Tet *> solids;
  solids.reserve(elems.size());

  std::vector<G4Material *> unique_mats;
  unique_mats.reserve(std::min<size_t>(64, elems.size()));

  std::unordered_map<const G4Material *, unsigned int> mat_ptr_to_index;
  std::vector<unsigned int> mat_index_per_copy;
  mat_index_per_copy.reserve(elems.size());
  std::vector<int> region_per_copy;
  region_per_copy.reserve(elems.size());

  auto get_or_add_material_index = [&](G4Material *m) -> unsigned int {
    auto it = mat_ptr_to_index.find(m);
    if (it != mat_ptr_to_index.end()) return it->second;
    const unsigned int idx = static_cast<unsigned int>(unique_mats.size());
    unique_mats.push_back(m);
    mat_ptr_to_index.emplace(m, idx);
    return idx;
  };


auto node_at = [&](int id) -> const NodeRec & {
  // Accept both 0-based and 1-based .node indices
  if (node_table.index_base == 0) {
    if (id < 0 || id >= node_table.n_points)
      throw std::runtime_error("Invalid node index in .ele (0-based expected): " + std::to_string(id));
    return node_table.nodes[static_cast<size_t>(id)];
  } else {
    if (id <= 0 || id > node_table.n_points)
      throw std::runtime_error("Invalid node index in .ele (1-based expected): " + std::to_string(id));
    return node_table.nodes[static_cast<size_t>(id - 1)];
  }
};

  for (const auto &e : elems) {
    const auto &a = node_at(e.n1);
    const auto &b = node_at(e.n2);
    const auto &c = node_at(e.n3);
    const auto &d = node_at(e.n4);

    const G4ThreeVector p1(a.x, a.y, a.z);
    const G4ThreeVector p2(b.x, b.y, b.z);
    const G4ThreeVector p3(c.x, c.y, c.z);
    const G4ThreeVector p4(d.x, d.y, d.z);

    const auto solid_name = pv_name + std::string("_tet_") + std::to_string(e.id);
    solids.push_back(new G4Tet(solid_name,
                               p1 - mesh_center,
                               p2 - mesh_center,
                               p3 - mesh_center,
                               p4 - mesh_center));

    G4Material *mat = default_material;
    auto mit = region_to_material.find(e.region);
    if (mit != region_to_material.end() && mit->second != nullptr) mat = mit->second;

    mat_index_per_copy.push_back(get_or_add_material_index(mat));
    region_per_copy.push_back(e.region);
  }

  // Dummy LV (required by G4PVParameterised). Actual solids come from ComputeSolid().
  auto *dummy_solid = new G4Box((pv_name + "_dummy_box").c_str(), 0.5 * mm, 0.5 * mm, 0.5 * mm);
  auto *tet_lv = new G4LogicalVolume(dummy_solid, default_material, (pv_name + "_lv").c_str());

  auto param = std::make_unique<GateTetrahedralMeshParameterisation>(std::move(solids),
                                                    unique_mats,
                                                    mat_index_per_copy,
                                                    region_per_copy,
                                                    region_to_colour,
                                                    region_visible);
  auto *param_ptr = param.get();
  g_tetrahedral_mesh_parameterisations.emplace_back(std::move(param));

  // ONLY DAUGHTER RULE: mother_lv must have no other daughters.
  auto *pv = new G4PVParameterised(pv_name.c_str(), tet_lv, mother_lv, kUndefined,
                                  static_cast<G4int>(mat_index_per_copy.size()), param_ptr, check_overlaps);
  return pv;
}
