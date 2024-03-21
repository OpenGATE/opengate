/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateKillNonInteractingParticleActor.h"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "G4PhysicalVolumeStore.hh"
#include "G4LogicalVolumeStore.hh"


GateKillNonInteractingParticleActor::GateKillNonInteractingParticleActor(py::dict &user_info)
    : GateVActor(user_info, false) {
  fActions.insert("StartSimulationAction");
  fActions.insert("SteppingAction");
  fActions.insert("PreUserTrackingAction");
}




void GateKillNonInteractingParticleActor::ActorInitialize() {}

void GateKillNonInteractingParticleActor::StartSimulationAction() {
  fNbOfKilledParticles = 0;  
}


void GateKillNonInteractingParticleActor::PreUserTrackingAction(const G4Track* track) {
  fIsFirstStep = true;
  fKineticEnergyAtTheEntrance = 0;
  ftrackIDAtTheEntrance = 0;
  fPassedByTheMotherVolume = false;

}

void GateKillNonInteractingParticleActor::SteppingAction(G4Step *step) {

  G4String logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
  if ((fPassedByTheMotherVolume) && (step->GetPostStepPoint()->GetStepStatus() == 1)){
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),logicalVolumeNamePostStep  ) !=fListOfVolumeAncestor.end()){
      if ((step->GetTrack()->GetTrackID() == ftrackIDAtTheEntrance) && (step->GetPostStepPoint()->GetKineticEnergy() == fKineticEnergyAtTheEntrance)){
        auto track = step->GetTrack();
        track->SetTrackStatus(fStopAndKill);
        fNbOfKilledParticles++;
    }
  }
}

   G4String logNameMotherVolume = G4LogicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName)->GetName();
   G4String physicalVolumeNamePreStep = step->GetPreStepPoint()->GetPhysicalVolume()->GetName();
    if ((step->GetTrack()->GetLogicalVolumeAtVertex()->GetName()  != logNameMotherVolume) && (fIsFirstStep)){
      if ((fPassedByTheMotherVolume == false) && (physicalVolumeNamePreStep == fMotherVolumeName) && (step->GetPreStepPoint()->GetStepStatus() == 1)){
        fPassedByTheMotherVolume =true;
        fKineticEnergyAtTheEntrance = step->GetPreStepPoint()->GetKineticEnergy();
        ftrackIDAtTheEntrance = step->GetTrack()->GetTrackID();
    }
  }
  
  fIsFirstStep = false;
}
