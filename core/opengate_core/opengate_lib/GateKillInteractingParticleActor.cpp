/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateKillInteractingParticleActor.h"
#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

GateKillInteractingParticleActor::GateKillInteractingParticleActor(
    py::dict &user_info)
    : GateVActor(user_info, false) {
}


void GateKillInteractingParticleActor::StartSimulationAction() {
  fNbOfKilledParticles = 0;
}

void GateKillInteractingParticleActor::PreUserTrackingAction(
    const G4Track *track) {
  fIsFirstStep = true;
}

void GateKillInteractingParticleActor::SteppingAction(G4Step *step) {

  G4String logNameMotherVolume = G4LogicalVolumeStore::GetInstance() ->GetVolume(fMotherVolumeName)->GetName();
  G4String physicalVolumeNamePreStep = "None";
  if (step->GetPreStepPoint() != 0)
    physicalVolumeNamePreStep =step->GetPreStepPoint()->GetPhysicalVolume()->GetName();
  if ((step->GetTrack()->GetLogicalVolumeAtVertex()->GetName() != logNameMotherVolume) && (fIsFirstStep)) {
    if ((physicalVolumeNamePreStep == fMotherVolumeName) && (step->GetPreStepPoint()->GetStepStatus() == 1)) {
      fKineticEnergyAtTheEntrance = step->GetPreStepPoint()->GetKineticEnergy();
      ftrackIDAtTheEntrance = step->GetTrack()->GetTrackID();
    }
  }

  G4String logicalVolumeNamePostStep = step->GetPostStepPoint()
                                           ->GetPhysicalVolume()
                                           ->GetLogicalVolume()
                                           ->GetName();

  if (step->GetPostStepPoint()->GetStepStatus() == 1) {
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),
                  logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()) {
      if ((step->GetTrack()->GetTrackID() != ftrackIDAtTheEntrance) ||
          (step->GetPostStepPoint()->GetKineticEnergy() !=
           fKineticEnergyAtTheEntrance)) {
        auto track = step->GetTrack();
        track->SetTrackStatus(fStopAndKill);
        fNbOfKilledParticles++;
      }
      fKineticEnergyAtTheEntrance = 0;
      ftrackIDAtTheEntrance = 0;
    }
  }
  fIsFirstStep = false;
}
