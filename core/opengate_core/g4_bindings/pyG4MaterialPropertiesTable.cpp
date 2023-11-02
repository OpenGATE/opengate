#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4MaterialPropertiesIndex.hh"
#include "G4MaterialPropertiesTable.hh"
#include "G4MaterialPropertyVector.hh"

void init_G4MaterialPropertiesTable(py::module &m) {

  py::class_<G4MaterialPropertiesTable,
             std::unique_ptr<G4MaterialPropertiesTable, py::nodelete>>(
      m, "G4MaterialPropertiesTable")

      .def(py::init())

      .def("GetMaterialConstPropertyNames",
           &G4MaterialPropertiesTable::GetMaterialConstPropertyNames,
           py::return_value_policy::copy)

      // .def("AddConstProperty", &G4MaterialPropertiesTable::AddConstProperty)

      .def(
          "AddConstProperty",
          [](G4MaterialPropertiesTable &mpt, const G4String &key,
             G4double propertyValue, G4bool createNewKey) {
            return mpt.AddConstProperty(key.c_str(), propertyValue,
                                        createNewKey);
          },
          py::return_value_policy::reference_internal)

      .def(
          "GetConstProperty",
          [](const G4MaterialPropertiesTable &mpt, const std::string &key) {
            return mpt.GetConstProperty(key.c_str());
          },
          py::return_value_policy::automatic)

      .def(
          "AddProperty",
          [](G4MaterialPropertiesTable &mpt, const G4String &key,
             const std::vector<G4double> &photonEnergies,
             const std::vector<G4double> &propertyValues, G4bool createNewKey,
             G4bool spline) {
            return mpt.AddProperty(key, photonEnergies, propertyValues,
                                   createNewKey, spline);
          },
          py::return_value_policy::reference_internal)

      .def("DumpTable", &G4MaterialPropertiesTable::DumpTable)

      .def("GetMaterialPropertyNames",
           &G4MaterialPropertiesTable::GetMaterialPropertyNames,
           py::return_value_policy::copy)

      .def("GetMaterialConstPropertyNames",
           &G4MaterialPropertiesTable::GetMaterialConstPropertyNames,
           py::return_value_policy::copy);
}
