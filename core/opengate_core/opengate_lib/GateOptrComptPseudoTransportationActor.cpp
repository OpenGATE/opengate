//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
//
/// \file GateOptrComptPseudoTransportationActor.cc
/// \brief Implementation of the GateOptrComptPseudoTransportationActor class

#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "G4BiasingProcessInterface.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GateOptnComptSplittingForTransportation.h"
#include "GateOptrComptPseudoTransportationActor.h"
#include "G4ProcessManager.hh"
#include "G4VEmProcess.hh"
#include "G4EmCalculator.hh"
#include "G4ProcessVector.hh"
#include "G4ParticleTable.hh"
#include "G4Gamma.hh"
#include "CLHEP/Units/SystemOfUnits.h"
#include "G4TrackStatus.hh"
#include "G4UserTrackingAction.hh"
#include "G4RunManager.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptrComptPseudoTransportationActor::GateOptrComptPseudoTransportationActor(py::dict &user_info)
    : G4VBiasingOperator("ComptSplittingOperator"),
      GateVActor(user_info, false) {
  fMotherVolumeName = DictGetStr(user_info, "mother");
  fSplittingFactor = DictGetDouble(user_info, "splitting_factor");
  fWeightThreshold = DictGetDouble(user_info, "weight_threshold");
  fRelativeMinWeightOfParticle = DictGetDouble(user_info, "relative_min_weight_of_particle");
  //Since the russian roulette uses as a probability 1/splitting, we need to have a double,
  //but the splitting factor provided by the user is logically an int, so we need to change the type.
  fRotationVectorDirector = DictGetBool(user_info, "rotation_vector_director");
  fRussianRoulette = DictGetBool(user_info, "russian_roulette");
  fVectorDirector = DictGetG4ThreeVector(user_info, "vector_director");
  fMaxTheta = DictGetDouble(user_info,"max_theta");
  fRussianRouletteForFreeFlight = DictGetDouble(user_info,"russian_roulette_for_free_flight");
  fFreeFlightOperation = new GateOptnForceFreeFlight("freeFlightOperation");
  fComptSplittingOperation = new GateOptnComptSplittingForTransportation("comptSplittingOperation");
  fUseProbes = DictGetBool(user_info,"use_probes");
  fActions.insert("StartSimulationAction");
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("PostUserTrackingAction");
  isSplitted = false;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void GateOptrComptPseudoTransportationActor::AttachAllLogicalDaughtersVolumes(G4LogicalVolume* volume){
  AttachTo(volume);
  G4int nbOfDaughters = volume->GetNoDaughters();
  if (nbOfDaughters >0 ){
    for (int i = 0; i< nbOfDaughters;i++){
      G4LogicalVolume* logicalDaughtersVolume = volume->GetDaughter(i)->GetLogicalVolume();
      AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
    }
  }
}

void GateOptrComptPseudoTransportationActor::StartSimulationAction(){
  G4LogicalVolume* biasingVolume = G4LogicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);

  //Here we need to attach all the daughters and daughters of daughters (...) to the biasing operator.
  //To do that, I use the function AttachAllLogicalDaughtersVolumes.
  AttachAllLogicalDaughtersVolumes(biasingVolume);
  fComptSplittingOperation->SetSplittingFactor(fSplittingFactor);
  fComptSplittingOperation->SetWeightThreshold(fWeightThreshold);
  fComptSplittingOperation->SetMaxTheta(fMaxTheta);
  fComptSplittingOperation->SetRussianRoulette(fRussianRoulette);
  fComptSplittingOperation->SetUseOfProbes(fUseProbes);
  fFreeFlightOperation->SetRussianRouletteProbability(fRussianRouletteForFreeFlight);
  fFreeFlightOperation->SetUseOfProbes(fUseProbes);

  
}

void GateOptrComptPseudoTransportationActor::StartRun() {

  // The way to behave of the russian roulette is the following :
  // we provide a vector director and the theta angle acceptance, where theta = 0 is a vector colinear to the vector director
  // Then if the track generated is on the acceptance angle, we add it to the primary track, and if it's not the case, we launch the russian roulette
  if (fRotationVectorDirector){
    G4VPhysicalVolume* physBiasingVolume = G4PhysicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);
    auto rot = physBiasingVolume -> GetObjectRotationValue();
    fVectorDirector = rot * fVectorDirector;
    fComptSplittingOperation->SetRotationMatrix(rot);
  }
  
  fComptSplittingOperation->SetVectorDirector(fVectorDirector);
  
  
}




void GateOptrComptPseudoTransportationActor::SteppingAction (G4Step *step) {

  //The stepping action is used to kill particle we have too kill :
    // - If the primary particle reach the biased boudary
    // - KIll all the probes exiting the volume
    // - Kill, if probes, particles wich have a weilght lower than the probes one
  
  if (fUseProbes) {
    if ((fKillOthersParticles) && (step->GetTrack()->IsGoodForTracking() ==0))
    {
      step->GetTrack()->SetTrackStatus(G4TrackStatus::fStopAndKill);
    }

    if (step->GetPostStepPoint()->GetStepStatus()!= fWorldBoundary){
      if ((step->GetPostStepPoint()->GetPhysicalVolume ()->GetName() == "world") && (step->GetTrack()->IsGoodForTracking() == 1)){
        step->GetTrack()->SetTrackStatus(G4TrackStatus::fStopAndKill);
      }
    }
  }

  if ((isSplitted ==true) &&  (step->GetPostStepPoint()->GetStepStatus()!= fWorldBoundary)){ 
    if ((step->GetPostStepPoint()->GetPhysicalVolume ()->GetName() == "world"))
    {
      step->GetTrack()->SetTrackStatus(G4TrackStatus::fStopAndKill);
      isSplitted =false;
    }
  }



  
}

void GateOptrComptPseudoTransportationActor::BeginOfEventAction(const G4Event *event) {
  fKillOthersParticles = false;
}

void GateOptrComptPseudoTransportationActor::StartTracking(const G4Track *track) {
fInitialWeight = track->GetWeight();
}


//For the following operation the idea is the following :
//All the potential photon processes are biased. If a particle undergoes a compton interaction, we splitted it 
//(ComptonSplittingForTransportation operation) and the particle generated are pseudo-transported with the ForceFreeFLight operation
// Since the occurence Biaising operation is called at the beginning of each track, and propose a different way to track the particle 
//(with modified physics), it here returns other thing than 0 if we want to pseudo-transport the particle, so if its creatorProcess is the
//modified compton interaction

G4VBiasingOperation *
GateOptrComptPseudoTransportationActor::ProposeOccurenceBiasingOperation(const G4Track* track, const G4BiasingProcessInterface* callingProcess)
{


if (track->GetCreatorProcess () !=0){
    if (track->GetCreatorProcess ()->GetProcessName() == "biasWrapper(compt)"){
      fFreeFlightOperation->SetMinWeight(fInitialWeight/fRelativeMinWeightOfParticle);
      fFreeFlightOperation->SetTrackWeight(track->GetWeight());
      return fFreeFlightOperation;
    }
      
  }
  return 0;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

// Here we call the final state biasing operation called if one of the biased interaction (all photon interaction here) occurs.
//That's why we need here to apply some conditions to just split the initial track.

G4VBiasingOperation *
GateOptrComptPseudoTransportationActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
    G4String callingProcessName = "biasWrapper(compt)";

 if (callingProcess->GetWrappedProcess()->GetProcessName() == "compt")
 {
  if (track->GetCreatorProcess() ==0) {
    isSplitted = true;
    return fComptSplittingOperation;
  }
  if (track->GetCreatorProcess()-> GetProcessName() !=  "biasWrapper(compt)"){
    isSplitted = true;
    return fComptSplittingOperation;
  }
 }
 /*
 */
 if (track->GetCreatorProcess() !=0){
  if(track->GetCreatorProcess()-> GetProcessName() ==  "biasWrapper(compt)"){
    return callingProcess->GetCurrentOccurenceBiasingOperation();
  }
 }

 return 0;
 
 //return 0;
}



void GateOptrComptPseudoTransportationActor::EndTracking() {
isSplitted =false;
}


void GateOptrComptPseudoTransportationActor::PostUserTrackingAction(const G4Track *track) {

if (fUseProbes){
  if (track->IsGoodForTracking() == 1){
    G4double tmpWeight = fFreeFlightOperation->GetTrackWeight();
    if (NbOfProbe == 1)
    {
      fKillOthersParticles = false;
      weight = tmpWeight;
    }
    else{
      if (tmpWeight > weight){
        weight = tmpWeight;
      }
    }

    NbOfProbe ++;
    if ((NbOfProbe == 6)){
      if (weight <  fInitialWeight/fRelativeMinWeightOfParticle){
        fKillOthersParticles = true;
      }
        NbOfProbe = 1;
        weight = 0;

    }
  }
}
}




//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
