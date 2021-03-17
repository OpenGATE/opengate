/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4NistManager.hh"

void init_G4NistManager(py::module &m) {

    py::class_<G4NistManager>(m, "G4NistManager")

        .def("Instance", &G4NistManager::Instance, py::return_value_policy::reference)
        .def("SetVerbose", &G4NistManager::SetVerbose)
        .def("GetVerbose", &G4NistManager::GetVerbose)
        .def("GetElement", &G4NistManager::GetElement, py::return_value_policy::reference_internal)
        .def("GetNistElementNames", &G4NistManager::GetNistElementNames)
        .def("GetNistMaterialNames", &G4NistManager::GetNistMaterialNames)
        .def("FindOrBuildElement",
             [](G4NistManager *mm,
                const G4String &symb,
                G4bool isotopes = true) {
                 return mm->FindOrBuildElement(symb, isotopes);
             },
             py::arg("symb"),
             py::arg("isotopes") = true,
             py::return_value_policy::reference_internal)
        .def("FindOrBuildMaterial",
             [](G4NistManager *mm,
                const G4String &symb,
                G4bool isotopes = true,
                G4bool warning = false) {
                 return mm->FindOrBuildMaterial(symb, isotopes, warning);
             },
             py::arg("symb"),
             py::arg("isotopes") = true,
             py::arg("warning") = false,
             py::return_value_policy::reference_internal)

        .def("ConstructNewMaterial",
             [](G4NistManager *mm,
                const G4String &name,
                const std::vector<G4String> &elm,
                const std::vector<G4int> &nbAtoms,
                G4double dens) {
                 return mm->ConstructNewMaterial(name, elm, nbAtoms, dens);
             }, py::return_value_policy::reference_internal)

        .def("GetNumberOfElements", &G4NistManager::GetNumberOfElements)
        .def("GetZ", &G4NistManager::GetZ)
        .def("GetIsotopeMass", &G4NistManager::GetIsotopeMass)
        .def("PrintG4Element", &G4NistManager::PrintG4Element)
        .def("GetMaterial", &G4NistManager::GetMaterial, py::return_value_policy::reference)
        .def("ConstructNewGasMaterial", &G4NistManager::ConstructNewGasMaterial, py::return_value_policy::reference)

        .def("GetNumberOfMaterials", &G4NistManager::GetNumberOfMaterials)
        .def("ListMaterials", &G4NistManager::ListMaterials)
        .def("PrintG4Material", &G4NistManager::PrintG4Material);
}
