/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

namespace py = pybind11;

#include "G4UnitsTable.hh"

void init_G4UnitsTable(py::module &m) {

    py::class_<G4UnitsCategory>(m, "G4UnitsCategory")
        //.def(py::init<const G4String &>())
        .def("GetName", &G4UnitsCategory::GetName,
             py::return_value_policy::copy)
        .def("GetUnitsList", &G4UnitsCategory::GetUnitsList,
             py::return_value_policy::reference)
        .def("GetNameMxLen", &G4UnitsCategory::GetNameMxLen)
        .def("GetSymbMxLen", &G4UnitsCategory::GetSymbMxLen)
        .def("UpdateNameMxLen", &G4UnitsCategory::UpdateNameMxLen)
        .def("UpdateSymbMxLen", &G4UnitsCategory::UpdateSymbMxLen)
        .def("PrintCategory", &G4UnitsCategory::PrintCategory);

    py::class_<G4UnitDefinition>(m, "G4UnitDefinition")
        .def(py::init<const G4String &, const G4String &, const G4String &, G4double>())

        .def("GetName", &G4UnitDefinition::GetName,
             py::return_value_policy::copy)
        .def("GetSymbol", &G4UnitDefinition::GetSymbol,
             py::return_value_policy::copy)
        .def("GetValue", &G4UnitDefinition::GetValue)
        .def("PrintDefinition", &G4UnitDefinition::PrintDefinition)
        .def("BuildUnitsTable", &G4UnitDefinition::BuildUnitsTable)
        .def("PrintUnitsTable", &G4UnitDefinition::PrintUnitsTable)
        .def("GetUnitsTable", &G4UnitDefinition::GetUnitsTable,
             py::return_value_policy::reference)
        .def("GetValueOf", &G4UnitDefinition::GetValueOf)
        .def("GetCategory", &G4UnitDefinition::GetCategory);

    py::class_<G4BestUnit>(m, "G4BestUnit")
        .def(py::init<G4double, const G4String &>())
        .def(py::init<const G4ThreeVector &, const G4String &>())
        .def("GetCategory", &G4BestUnit::GetCategory, py::return_value_policy::copy)
        .def("__str__", [](const G4BestUnit &a) {
            std::ostringstream oss;
            oss << a;
            return oss.str();
        })
        .def("GetIndexOfCategory", &G4BestUnit::GetIndexOfCategory);


    //py::bind_vector<std::vector<G4UnitsCategory*>>(m, "G4UnitsTable");
    py::bind_vector<G4UnitsTable>(m, "G4UnitsTable");
    //py::class_<G4UnitsTable, std::vector<G4UnitsCategory*>>(m, "G4UnitsTable")
    //            .def(py::init());

}

