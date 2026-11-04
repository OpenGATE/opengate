/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateKillNonInteractingParticleForLVActor.h"
#include <G4AutoLock.hh>
#include <algorithm>

namespace {
G4Mutex KillNonInteractingParticleForLVMutex = G4MUTEX_INITIALIZER;
}

GateKillNonInteractingParticleForLVActor::
    GateKillNonInteractingParticleForLVActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfSimulationWorkerAction");
}

void GateKillNonInteractingParticleForLVActor::StartSimulationAction() {
  fNbOfKilledParticles = 0;
}

void GateKillNonInteractingParticleForLVActor::PreUserTrackingAction(
    const G4Track *) {
  auto &data = fWorkerState.Get();
  data.fIsFirstStep = true;
  data.fKineticEnergyAtTheEntrance = 0;
  data.fTrackIDAtTheEntrance = 0;
  data.fPassedByTheMotherVolume = false;
}

void GateKillNonInteractingParticleForLVActor::SteppingAction(G4Step *step) {
  auto &data = fWorkerState.Get();
  const auto *pre = step->GetPreStepPoint();
  const auto *post = step->GetPostStepPoint();
  const auto *preVolume = pre->GetPhysicalVolume();

  // Keep the historical entry rule: tracks born in the volume are exempt.
  if (data.fIsFirstStep &&
      step->GetTrack()->GetLogicalVolumeAtVertex()->GetName() !=
          fAttachedToVolumeName &&
      !data.fPassedByTheMotherVolume && preVolume &&
      pre->GetStepStatus() == fGeomBoundary &&
      preVolume->GetName() == fAttachedToVolumeName) {
    data.fPassedByTheMotherVolume = true;
    data.fKineticEnergyAtTheEntrance = pre->GetKineticEnergy();
    data.fTrackIDAtTheEntrance = step->GetTrack()->GetTrackID();
  }

  // At a world exit there is no post volume; do not dereference it.
  const auto *postVolume = post->GetPhysicalVolume();
  if (data.fPassedByTheMotherVolume &&
      post->GetStepStatus() == fGeomBoundary && postVolume) {
    const auto &postName = postVolume->GetLogicalVolume()->GetName();
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),
                  postName) != fListOfVolumeAncestor.end() &&
        step->GetTrack()->GetTrackID() == data.fTrackIDAtTheEntrance &&
        post->GetKineticEnergy() == data.fKineticEnergyAtTheEntrance) {
      step->GetTrack()->SetTrackStatus(fStopAndKill);
      ++data.fNbOfKilledParticles;
    }
  }
  data.fIsFirstStep = false;
}

void GateKillNonInteractingParticleForLVActor::EndOfSimulationWorkerAction(
    const G4Run *) {
  auto &data = fWorkerState.Get();
  G4AutoLock lock(&KillNonInteractingParticleForLVMutex);
  fNbOfKilledParticles += data.fNbOfKilledParticles;
  data.fNbOfKilledParticles = 0;
}
