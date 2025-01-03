/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ProductionCutsTable.hh"

void init_G4ProductionCutsTable(py::module &m) {

  py::class_<G4ProductionCutsTable>(m, "G4ProductionCutsTable")
      .def("GetProductionCutsTable",
           &G4ProductionCutsTable::GetProductionCutsTable,
           py::return_value_policy::reference)
      .def("SetEnergyRange", &G4ProductionCutsTable::SetEnergyRange)
      .def("GetTableSize", &G4ProductionCutsTable::GetTableSize)
      .def(
          "GetMaterialCutsCouple",
          [](const G4ProductionCutsTable &table,
             G4int i) -> const G4MaterialCutsCouple * {
            return table.GetMaterialCutsCouple(i);
          },
          py::return_value_policy::reference)
      .def("GetLowEdgeEnergy", &G4ProductionCutsTable::GetLowEdgeEnergy)
      .def("GetHighEdgeEnergy", &G4ProductionCutsTable::GetHighEdgeEnergy)
      .def("ResetConverters", &G4ProductionCutsTable::ResetConverters)
      .def("DumpCouples", &G4ProductionCutsTable::DumpCouples);
}
