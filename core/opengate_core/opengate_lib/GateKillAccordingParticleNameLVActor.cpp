/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateKillAccordingParticleNameLVActor.h"
#include "GateHelpersDict.h"
#include <G4AutoLock.hh>
#include <algorithm>

namespace {
G4Mutex KillAccordingParticleNameLVMutex = G4MUTEX_INITIALIZER;
}

GateKillAccordingParticleNameLVActor::GateKillAccordingParticleNameLVActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfSimulationWorkerAction");
}

void GateKillAccordingParticleNameLVActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fParticlesNameToKill = DictGetVecStr(user_info, "particles_name_to_kill");
}

void GateKillAccordingParticleNameLVActor::StartSimulationAction() {
  fNbOfKilledParticles = 0;
}

void GateKillAccordingParticleNameLVActor::PreUserTrackingAction(
    const G4Track *track) {
  const auto &name = track->GetParticleDefinition()->GetParticleName();
  fThreadLocalData.Get().fIsAParticleToKill =
      std::find(fParticlesNameToKill.begin(), fParticlesNameToKill.end(), name) !=
      fParticlesNameToKill.end();
}

void GateKillAccordingParticleNameLVActor::SteppingAction(G4Step *step) {
  auto &data = fThreadLocalData.Get();
  if (!data.fIsAParticleToKill ||
      step->GetPostStepPoint()->GetStepStatus() != fGeomBoundary)
    return;
  const auto *volume = step->GetPostStepPoint()->GetPhysicalVolume();
  if (!volume)
    return;
  const auto &name = volume->GetLogicalVolume()->GetName();
  if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(), name) !=
      fListOfVolumeAncestor.end()) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    ++data.fNbOfKilledParticles;
  }
}

void GateKillAccordingParticleNameLVActor::EndOfSimulationWorkerAction(
    const G4Run *) {
  auto &data = fThreadLocalData.Get();
  G4AutoLock lock(&KillAccordingParticleNameLVMutex);
  fNbOfKilledParticles += data.fNbOfKilledParticles;
  data.fNbOfKilledParticles = 0;
}
