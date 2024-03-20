/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateSurfaceSplittingActor.h"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "G4LogicalVolumeStore.hh"

GateSurfaceSplittingActor::GateSurfaceSplittingActor(py::dict &user_info)
    : GateVActor(user_info, false) {
  fActions.insert("StartSimulationAction");
  fActions.insert("SteppingAction");
  fActions.insert("PreUserTrackingAction");
  fMotherVolumeName = DictGetStr(user_info,"mother");
  fWeightThreshold = DictGetBool(user_info,"weight_threshold");
  fSplittingFactor = DictGetInt(user_info,"splitting_factor");
  fSplitEnteringParticles = DictGetBool(user_info,"split_entering_particles");
  fSplitExitingParticles = DictGetBool(user_info,"split_exiting_particles");
}

void GateSurfaceSplittingActor::ActorInitialize() {}

void GateSurfaceSplittingActor::StartSimulationAction() { fNbOfKilledParticles = 0; }

void GateSurfaceSplittingActor::PreUserTrackingAction(const G4Track* track){

  fIsFirstStep = true;
}

void GateSurfaceSplittingActor::SteppingAction(G4Step *step) {
  auto track = step->GetTrack();
  auto weight = track->GetWeight();


  if (weight >= fWeightThreshold){
    if (fSplitEnteringParticles){
      G4String logicalVolumeNamePreStep = step->GetPreStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();    
      if (((fIsFirstStep) && (step->GetPreStepPoint()->GetStepStatus() ==1) && (logicalVolumeNamePreStep == fMotherVolumeName))
          || ((fIsFirstStep) && (track->GetLogicalVolumeAtVertex()->GetName() != logicalVolumeNamePreStep) && (track->GetLogicalVolumeAtVertex()->GetName() != fMotherVolumeName))) {
        G4ThreeVector position = step->GetPreStepPoint()->GetPosition();
        G4ThreeVector momentum = step->GetPreStepPoint()->GetMomentum();
        G4double ekin = step->GetPreStepPoint()->GetKineticEnergy();
        
        const G4DynamicParticle* particleType = track->GetDynamicParticle();
        G4double time = step->GetPreStepPoint()->GetGlobalTime();
        G4TrackVector *trackVector = step->GetfSecondary();
        
        for (int i = 0; i < fSplittingFactor -1 ; i++) {
          G4DynamicParticle* particleTypeToAdd = new G4DynamicParticle(*particleType); 
          G4Track* clone = new G4Track(particleTypeToAdd ,time,position);
          clone->SetKineticEnergy(ekin);
          clone->SetMomentumDirection(momentum);
          clone->SetWeight( weight/fSplittingFactor);
          trackVector->push_back(clone);
        }
        step->GetPreStepPoint()->SetWeight(weight/fSplittingFactor);
        step->GetPostStepPoint()->SetWeight(weight/fSplittingFactor);
        track->SetWeight(weight/fSplittingFactor);

      
      }
    }

  
    if(fSplitExitingParticles){
      G4String logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
      if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),logicalVolumeNamePostStep) !=fListOfVolumeAncestor.end()){
        G4TrackVector *trackVector = step->GetfSecondary();
        for (int i = 0; i < fSplittingFactor-1; i++) {
          G4Track* clone = new G4Track(*track);
          clone->SetWeight( weight/fSplittingFactor);
          trackVector->push_back(clone);
        }
        step->GetPostStepPoint()->SetWeight(weight/fSplittingFactor);
        track->SetWeight(weight/fSplittingFactor);
      }
    }
    
  }
  fIsFirstStep =false;
}
