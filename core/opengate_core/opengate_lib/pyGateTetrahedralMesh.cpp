/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <map>
#include <string>
#include <unordered_map>
#include <vector>

#include "G4Colour.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "GateTetrahedralMeshParameterisation.h"

namespace py = pybind11;

static std::unordered_map<int, G4Colour> rgba_to_colour_map(
    const std::unordered_map<int, std::vector<double>> &rgba_by_region) {
  std::unordered_map<int, G4Colour> colours;
  colours.reserve(rgba_by_region.size());
  for (const auto &entry : rgba_by_region) {
    const auto &rgba = entry.second;
    double red = 0.8;
    double green = 0.8;
    double blue = 0.8;
    double alpha = 1.0;
    if (rgba.size() >= 3) {
      red = rgba[0];
      green = rgba[1];
      blue = rgba[2];
    }
    if (rgba.size() >= 4) {
      alpha = rgba[3];
    }
    colours.emplace(entry.first, G4Colour(red, green, blue, alpha));
  }
  return colours;
}

void init_GateTetrahedralMesh(py::module &m) {
  m.def(
      "build_tetrahedral_mesh_from_tetgen",
      [](const std::string &node_path, const std::string &ele_path,
         G4LogicalVolume *mother_lv,
         const std::map<int, G4Material *> &region_to_material,
         const std::unordered_map<int, std::vector<double>> &region_to_rgba,
         const std::unordered_map<int, bool> &region_visible,
         G4Material *default_material, const std::string &pv_name,
         G4bool check_overlaps, G4double scale) {
        return build_tetrahedral_mesh_from_tetgen(
            node_path, ele_path, mother_lv, region_to_material,
            rgba_to_colour_map(region_to_rgba), region_visible,
            default_material, pv_name, check_overlaps, scale);
      },
      py::return_value_policy::reference, py::arg("node_path"),
      py::arg("ele_path"), py::arg("mother_lv"), py::arg("region_to_material"),
      py::arg("region_to_rgba") =
          std::unordered_map<int, std::vector<double>>{},
      py::arg("region_visible") = std::unordered_map<int, bool>{},
      py::arg("default_material") = nullptr,
      py::arg("pv_name") = std::string("phantom_tetmesh"),
      py::arg("check_overlaps") = false, py::arg("scale") = 1.0);

  m.def(
      "build_mrcp_tetrahedral_mesh_from_tetgen",
      [](const std::string &node_path, const std::string &ele_path,
         G4LogicalVolume *mother_lv,
         const std::map<int, G4Material *> &region_to_material,
         const std::unordered_map<int, std::vector<double>> &region_to_rgba,
         const std::unordered_map<int, bool> &region_visible,
         G4Material *default_material, const std::string &pv_name,
         G4bool check_overlaps) {
        return build_mrcp_tetrahedral_mesh_from_tetgen(
            node_path, ele_path, mother_lv, region_to_material,
            rgba_to_colour_map(region_to_rgba), region_visible,
            default_material, pv_name, check_overlaps);
      },
      py::return_value_policy::reference, py::arg("node_path"),
      py::arg("ele_path"), py::arg("mother_lv"), py::arg("region_to_material"),
      py::arg("region_to_rgba") =
          std::unordered_map<int, std::vector<double>>{},
      py::arg("region_visible") = std::unordered_map<int, bool>{},
      py::arg("default_material") = nullptr,
      py::arg("pv_name") = std::string("phantom_tetmesh"),
      py::arg("check_overlaps") = false);

  m.def("build_tetrahedral_mesh_from_tetgen_material_names",
        &build_tetrahedral_mesh_from_tetgen_material_names,
        py::return_value_policy::reference, py::arg("mother_lv"),
        py::arg("pv_name"), py::arg("node_path"), py::arg("ele_path"),
        py::arg("region_id_to_mat_name"), py::arg("scale") = 1.0,
        py::arg("check_overlaps") = false);
}
