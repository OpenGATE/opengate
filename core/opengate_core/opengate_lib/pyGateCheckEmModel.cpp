/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4LogicalVolume.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessTable.hh"
#include "G4VEmModel.hh"
#include "G4VEmProcess.hh"
#include "G4VEnergyLossProcess.hh"
#include "G4VProcess.hh"
#include <pybind11/pybind11.h>

namespace py = pybind11;

py::object check_em_model_in_volume(G4LogicalVolume *logicalVolume,
                                    const G4String &particleName,
                                    const G4String &processName,
                                    G4double kineticEnergy) {
  if (nullptr == logicalVolume) {
    return py::none();
  }

  const auto *couple = logicalVolume->GetMaterialCutsCouple();
  if (nullptr == couple) {
    return py::none();
  }

  auto *particle =
      G4ParticleTable::GetParticleTable()->FindParticle(particleName);
  if (nullptr == particle) {
    return py::none();
  }

  auto *process =
      G4ProcessTable::GetProcessTable()->FindProcess(processName, particle);
  if (nullptr == process) {
    return py::none();
  }

  const auto coupleIndex = static_cast<std::size_t>(couple->GetIndex());
  G4VEmModel *model = nullptr;

  if (auto *eloss = dynamic_cast<G4VEnergyLossProcess *>(process)) {
    auto idx = coupleIndex;
    model = eloss->SelectModelForMaterial(kineticEnergy, idx);
  } else if (auto *emproc = dynamic_cast<G4VEmProcess *>(process)) {
    auto idx = coupleIndex;
    model = emproc->SelectModelForMaterial(kineticEnergy, idx);
  }

  if (nullptr == model) {
    return py::none();
  }
  return py::str(model->GetName());
}

void init_GateCheckEmModel(py::module &m) {
  m.def("check_em_model_in_volume", check_em_model_in_volume);
}
