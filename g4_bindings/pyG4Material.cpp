/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4Material.hh"
#include "G4Element.hh"
#include "G4UnitsTable.hh"

void init_G4Material(py::module &m) {

    py::class_<G4Material>(m, "G4Material")

            // name density nbcompo solid/gas temp pressure
            .def(py::init<const G4String &, G4double, G4int, G4State, G4double, G4double>())

                    // stream output /// FIXME not sure this is the right way to do
            .def("__repr__", [](const G4Material &material) {
                std::ostringstream flux;
                flux << material;
                return flux.str();
            })

            .def("AddElement", [](G4Material &ma, G4Element *element, G4int nAtoms) {
                ma.AddElement(element, nAtoms);
            })
            .def("AddElement", [](G4Material &ma, G4Element *element, G4double fraction) {
                ma.AddElement(element, fraction);
            })

            .def("AddMaterial", &G4Material::AddMaterial)
            .def("GetName", &G4Material::GetName, py::return_value_policy::reference)
                    //         return_value_policy<reference_existing_object>())
            .def("GetChemicalFormula", &G4Material::GetChemicalFormula, py::return_value_policy::reference)
                    //   return_value_policy<reference_existing_object>())
            .def("SetName", &G4Material::SetName)
            .def("SetChemicalFormula", &G4Material::SetChemicalFormula)
            .def("GetDensity", &G4Material::GetDensity)
            .def("GetState", &G4Material::GetState)
            .def("GetTemperature", &G4Material::GetTemperature)
            .def("GetPressure", &G4Material::GetPressure)

            .def("GetElementVector", &G4Material::GetElementVector, py::return_value_policy::reference_internal)
                    //	 return_internal_reference<>())
            .def("GetElement", &G4Material::GetElement, py::return_value_policy::reference)
                    //   return_value_policy<reference_existing_object>())

            .def("GetTotNbOfAtomsPerVolume", &G4Material::GetTotNbOfAtomsPerVolume)
            .def("GetTotNbOfElectPerVolume", &G4Material::GetTotNbOfElectPerVolume)
                    // .def("GetFractionVector",         f_GetFractionVector)
                    // .def("GetAtomsVector",            f_GetAtomsVector)
                    // .def("GetVecNbOfAtomsPerVolume",  f_GetVecNbOfAtomsPerVolume)
                    // .def("GetAtomicNumDensityVector", f_GetAtomicNumDensityVector)

            .def("GetElectronDensity", &G4Material::GetElectronDensity)
            .def("GetRadlen", &G4Material::GetRadlen)
            .def("GetNuclearInterLength", &G4Material::GetNuclearInterLength)
            .def("GetIonisation", &G4Material::GetIonisation, py::return_value_policy::reference_internal)//,
                    //	 return_internal_reference<>())
            .def("GetSandiaTable", &G4Material::GetSandiaTable, py::return_value_policy::reference_internal)//,
                    //	 return_internal_reference<>())

            .def("GetZ", &G4Material::GetZ)
            .def("GetA", &G4Material::GetA)
            .def("SetMaterialPropertiesTable", &G4Material::SetMaterialPropertiesTable)
            .def("GetMaterialPropertiesTable", &G4Material::GetMaterialPropertiesTable,
                 py::return_value_policy::reference_internal)
                    //	 return_internal_reference<>())
            .def("GetMaterialTable", &G4Material::GetMaterialTable, py::return_value_policy::reference)
                    //	 return_value_policy<reference_existing_object>())

                    //    .staticmethod("GetMaterialTable")
            .def_property_readonly_static("GetMaterialTable",
                                          [](py::object) { return G4Material::GetMaterialTable(); })

            .def("GetNumberOfElements", &G4Material::GetNumberOfElements)
                    //.def("GetNumberOfMaterials", &G4Material::GetNumberOfMaterials)
                    //.staticmethod("GetNumberOfMaterials")
                    //.def_property_readonly_static("GetNumberOfMaterials",
                    //                              [](py::object) { return G4Material::GetNumberOfMaterials(); })

            .def("GetIndex", &G4Material::GetIndex)
                    // .def("GetMaterial",           f1_GetMaterial, f_GetMaterial()
                    //      [return_value_policy<reference_existing_object>()])
                    // .def("GetMaterial",           f2_GetMaterial,
                    //      return_value_policy<reference_existing_object>())
                    // .def("GetMaterial",           f3_GetMaterial,
                    //      return_value_policy<reference_existing_object>())

                    //.staticmethod("GetMaterial")
            .def_property_readonly_static("GetMaterial",
                                          [](py::object, const G4String &name,
                                             G4bool warning = true) { return G4Material::GetMaterial(name, warning); });

    py::enum_<G4State>(m, "G4State")
            .value("kStateUndefined", kStateUndefined)
            .value("kStateSolid", kStateSolid)
            .value("kStateLiquid", kStateLiquid)
            .value("kStateGas", kStateGas)
            .export_values();

}
