/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateKillAccordingParticleNameActor.h"
#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4TransportationManager.hh"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

G4Mutex SetNbKillAcordingParticleMutex = G4MUTEX_INITIALIZER;

GateKillAccordingParticleNameActor::GateKillAccordingParticleNameActor(
    py::dict &user_info)
    : GateVActor(user_info, false) {}

void GateKillAccordingParticleNameActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fParticlesNameToKill = DictGetVecStr(user_info, "particles_name_to_kill");
}

void GateKillAccordingParticleNameActor::PreUserTrackingAction(
    const G4Track *track) {
  auto &l = fThreadLocalData.Get();
  l.fIsAParticleToKill = false;

  G4String particleName = track->GetParticleDefinition()->GetParticleName();
  if (std::find(fParticlesNameToKill.begin(), fParticlesNameToKill.end(),
                particleName) != fParticlesNameToKill.end()) {
    l.fIsAParticleToKill = true;
  }
}

void GateKillAccordingParticleNameActor::SteppingAction(G4Step *step) {

  if (step->GetPostStepPoint()->GetStepStatus() == 1) {
    G4String logicalVolumeNamePostStep = step->GetPostStepPoint()
                                             ->GetPhysicalVolume()
                                             ->GetLogicalVolume()
                                             ->GetName();
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),
                  logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()) {
      auto &l = fThreadLocalData.Get();
      if (l.fIsAParticleToKill) {
        step->GetTrack()->SetTrackStatus(fStopAndKill);
        G4AutoLock mutex(&SetNbKillAcordingParticleMutex);
        fNbOfKilledParticles++;
      }
    }
  }
}