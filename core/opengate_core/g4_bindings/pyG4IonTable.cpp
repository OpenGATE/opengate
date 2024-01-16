/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4IonTable.hh"
#include "G4ParticleDefinition.hh"

void init_G4IonTable(py::module &m) {

  py::class_<G4IonTable, std::unique_ptr<G4IonTable, py::nodelete>>(
      m, "G4IonTable")
      .def("GetIonTable", &G4IonTable::GetIonTable,
           py::return_value_policy::reference)

      .def("GetNumberOfElements", &G4IonTable::GetNumberOfElements)
      .def("Entries", &G4IonTable::Entries)
      .def("size", &G4IonTable::size)
      .def("CreateAllIon", &G4IonTable::CreateAllIon)
      .def("CreateAllIsomer", &G4IonTable::CreateAllIsomer)

      .def("GetIon",
           (G4ParticleDefinition *
            (G4IonTable::*)(G4int Z, G4int A, G4int lvl)) &
               G4IonTable::GetIon,
           py::return_value_policy::reference)

      .def("GetIon",
           (G4ParticleDefinition *
            (G4IonTable::*)(G4int Z, G4int A, G4double E, G4int J)) &
               G4IonTable::GetIon,
           py::return_value_policy::reference)

      .def("GetIon",
           (G4ParticleDefinition * (G4IonTable::*)(G4int encoding)) &
               G4IonTable::GetIon,
           py::return_value_policy::reference)

      //.def("GetIonName", (G4String(G4IonTable::*)(G4int Z, G4int A, G4int lvl)
      // const) & G4IonTable::GetIonName)
      // FIXME WARNING adapted to work both with G4 v11.1.1 and G4 v11.1.2
      // to be changed when switch to 11.1.2
      .def("GetIonName",
           [](G4IonTable &t, G4int Z, G4int A, G4int lvl) -> G4String {
             return t.GetIonName(Z, A, lvl);
           })

      .def("DumpTable", &G4IonTable::DumpTable);
}
