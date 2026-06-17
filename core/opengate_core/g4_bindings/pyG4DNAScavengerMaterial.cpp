/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4DNAScavengerMaterial.hh"
#include "G4MolecularConfiguration.hh"
#include "G4MoleculeTable.hh"
#include "GateChemistryWorld.h"
#include "pybind11/pybind11.h"

namespace py = pybind11;

void init_G4DNAScavengerMaterial(py::module &m) {
  py::class_<G4DNAScavengerMaterial,
             std::unique_ptr<G4DNAScavengerMaterial, py::nodelete>>(
      m, "G4DNAScavengerMaterial")
      // TODO: This nominally "raw" Geant4 binding currently depends on the
      // GATE-side GateChemistryWorld helper. Longer term, a cleaner design
      // would either move this binding into the GATE layer, or expose a pure
      // Geant4-based construction path that avoids depending on Gate* types.
      .def(py::init([](GateChemistryWorld *chemistryWorld) {
             return new G4DNAScavengerMaterial(chemistryWorld);
           }),
           py::arg("chemistry_world"))
      .def("SetCounterAgainstTime",
           &G4DNAScavengerMaterial::SetCounterAgainstTime)
      .def("SetpH", &G4DNAScavengerMaterial::SetpH, py::arg("pH"))
      .def("GetpH", &G4DNAScavengerMaterial::GetpH)
      .def("GetScavengerNames",
           [](G4DNAScavengerMaterial &self) {
             py::list names;
             for (const auto *conf : self.GetScavengerList()) {
               names.append(conf->GetName());
             }
             return names;
           })
      .def(
          "GetSpeciesCount",
          [](G4DNAScavengerMaterial &self, const G4String &species_name) {
            auto *conf = G4MoleculeTable::Instance()->GetConfiguration(
                species_name, false);
            if (conf == nullptr) {
              throw std::runtime_error("Unknown scavenger-material species: " +
                                       std::string(species_name));
            }
            return self.GetNumberMoleculePerVolumeUnitForMaterialConf(conf);
          },
          py::arg("species_name"))
      .def(
          "GetSpeciesCountAtTime",
          [](G4DNAScavengerMaterial &self, const G4String &species_name,
             G4double time) {
            auto *conf = G4MoleculeTable::Instance()->GetConfiguration(
                species_name, false);
            if (conf == nullptr) {
              throw std::runtime_error("Unknown scavenger-material species: " +
                                       std::string(species_name));
            }
            return self.GetNMoleculesAtTime(conf, time);
          },
          py::arg("species_name"), py::arg("time"));
}
