/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4DNAMolecularReactionTable.hh"
#include "G4DNAScavengerProcess.hh"
#include "G4MolecularConfiguration.hh"
#include "G4VProcess.hh"
#include "GateChemistryWorld.h"
#include "pybind11/pybind11.h"

namespace py = pybind11;

void init_G4DNAScavengerProcess(py::module &m) {
  py::class_<G4DNAScavengerProcess, G4VProcess,
             std::unique_ptr<G4DNAScavengerProcess, py::nodelete>>(
      m, "G4DNAScavengerProcess")
      // TODO: This nominally "raw" Geant4 binding currently depends on the
      // GATE-side GateChemistryWorld helper. Longer term, a cleaner design
      // would either move this binding into the GATE layer, or expose a pure
      // Geant4-based construction path that avoids depending on Gate* types.
      .def(py::init(
               [](const G4String &name, GateChemistryWorld *chemistryWorld) {
                 return new G4DNAScavengerProcess(
                     name, *chemistryWorld->GetChemistryBoundary());
               }),
           py::arg("name"), py::arg("chemistry_world"))
      .def("SetReaction", &G4DNAScavengerProcess::SetReaction,
           py::arg("molecule_configuration"), py::arg("reaction_data"));
}
