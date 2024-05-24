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
/// \file GateOptrLastVertexInteractionSplittingActor.cc
/// \brief Implementation of the GateOptrLastVertexInteractionSplittingActor class

#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "CLHEP/Units/SystemOfUnits.h"
#include "G4BiasingProcessInterface.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4ProcessManager.hh"
#include "G4TrackingManager.hh"
#include "G4ProcessVector.hh"
#include "GateOptnComptSplitting.h"
#include "GateOptrLastVertexInteractionSplittingActor.h"
#include "G4ParticleChangeForGamma.hh"
#include "G4VParticleChange.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptrLastVertexInteractionSplittingActor::GateOptrLastVertexInteractionSplittingActor(py::dict &user_info)
    : G4VBiasingOperator("LastVertexInteractionOperator"),
      GateVActor(user_info, false) {
  fMotherVolumeName = DictGetStr(user_info, "mother");
  fSplittingFactor = DictGetDouble(user_info, "splitting_factor");
  fWeightThreshold = DictGetDouble(user_info, "weight_threshold");
  fMinWeightOfParticle = DictGetDouble(user_info, "min_weight_of_particle");
  // Since the russian roulette uses as a probablity 1/splitting, we need to
  // have a double, but the splitting factor provided by the user is logically
  // an int, so we need to change the type.
  fRotationVectorDirector = DictGetBool(user_info, "rotation_vector_director");
  fBiasPrimaryOnly = DictGetBool(user_info, "bias_primary_only");
  fBiasOnlyOnce = DictGetBool(user_info, "bias_only_once");
  fRussianRoulette = DictGetBool(user_info, "russian_roulette");
  fVectorDirector = DictGetG4ThreeVector(user_info, "vector_director");
  fMaxTheta = DictGetDouble(user_info, "max_theta");
  fComptSplittingOperation =
      new GateOptnComptSplitting("ComptSplittingOperation");
  fActions.insert("StartSimulationAction");
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfEventAction");
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void GateOptrLastVertexInteractionSplittingActor::ComptonSplitting(G4Step* CurrentStep,G4Track track,G4Step step,G4VProcess* process,G4int splittingFactor){
G4TrackVector *trackVector = CurrentStep->GetfSecondary();
std::cout<<track.GetKineticEnergy()<<std::endl;
for (int i =0; i <splittingFactor; i++){
    G4VParticleChange* processFinalState =  process->PostStepDoIt(track,step);

    //Add of splitted primaries
    G4ParticleChangeForGamma *gammaProcessFinalState = (G4ParticleChangeForGamma *)processFinalState;
    const G4ThreeVector momentum =gammaProcessFinalState->GetProposedMomentumDirection();
    G4double energy = gammaProcessFinalState->GetProposedKineticEnergy();
    G4double globalTime = track.GetGlobalTime();
    G4double gammaWeight = track.GetWeight();
    const G4ThreeVector position = step.GetPostStepPoint()->GetPosition();
    G4Track *newTrack = new G4Track(track);
    newTrack->SetWeight(gammaWeight);
    newTrack->SetKineticEnergy(energy);
    newTrack->SetMomentumDirection(momentum);
    newTrack->SetPosition(position);
    trackVector->push_back(newTrack);


    // Add of splitted secondaries (electrons)

    G4int NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
    for(int j=0; j <NbOfSecondaries; j++){
      G4Track* newTrack = processFinalState->GetSecondary(j);
      trackVector->push_back(newTrack);
    }
  }
}


void GateOptrLastVertexInteractionSplittingActor::SecondariesSplitting(G4Step* CurrentStep,G4Track track,G4Step step,G4VProcess* process,G4int splittingFactor){
G4TrackVector *trackVector = CurrentStep->GetfSecondary();
for (int i =0; i <splittingFactor; i++){
    G4VParticleChange* processFinalState =  process->PostStepDoIt(track,step);
    G4int NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
    std::cout<<NbOfSecondaries<<std::endl;
    for(int j=0; j <NbOfSecondaries; j++){
      G4Track* newTrack = processFinalState->GetSecondary(j);
      trackVector->push_back(newTrack);
    }
  }
}
    
void GateOptrLastVertexInteractionSplittingActor::AttachToAllLogicalDaughtersVolumes(
    G4LogicalVolume *volume) {
  AttachTo(volume);
  G4int nbOfDaughters = volume->GetNoDaughters();
  if (nbOfDaughters > 0) {
    for (int i = 0; i < nbOfDaughters; i++) {
      G4LogicalVolume *logicalDaughtersVolume =
          volume->GetDaughter(i)->GetLogicalVolume();
      AttachToAllLogicalDaughtersVolumes(logicalDaughtersVolume);
    }
  }
}

void GateOptrLastVertexInteractionSplittingActor::StartSimulationAction() {
  G4LogicalVolume *biasingVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);

  // Here we need to attach all the daughters and daughters of daughters (...)
  // to the biasing operator. To do that, I use the function
  // AttachAllLogicalDaughtersVolumes.
  AttachToAllLogicalDaughtersVolumes(biasingVolume);
  fComptSplittingOperation->SetSplittingFactor(fSplittingFactor);
  fComptSplittingOperation->SetWeightThreshold(fWeightThreshold);
  fComptSplittingOperation->SetMaxTheta(fMaxTheta);
  fComptSplittingOperation->SetRussianRoulette(fRussianRoulette);
  fComptSplittingOperation->SetMinWeightOfParticle(fMinWeightOfParticle);
}

void GateOptrLastVertexInteractionSplittingActor::StartRun() {

  // The way to behave of the russian roulette is the following :
  // we provide a vector director and the theta angle acceptance, where theta =
  // 0 is a vector colinear to the vector director Then if the track generated
  // is on the acceptance angle, we add it to the primary track, and if it's not
  // the case, we launch the russian roulette
  if (fRotationVectorDirector) {
    G4VPhysicalVolume *physBiasingVolume =
        G4PhysicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);
    auto rot = physBiasingVolume->GetObjectRotationValue();
    fVectorDirector = rot * fVectorDirector;
  }

  fComptSplittingOperation->SetVectorDirector(fVectorDirector);
}

void GateOptrLastVertexInteractionSplittingActor::StartTracking(const G4Track *track) {
  fNInteractions = 0;
}


void GateOptrLastVertexInteractionSplittingActor::RememberLastProcessInformation(G4Step* step){
  G4String processName = "None";
  if (step->GetPostStepPoint()->GetProcessDefinedStep() !=0){
    processName = step->GetPostStepPoint()->GetProcessDefinedStep()-> GetProcessName();
  }
  if ((std::find(fListOfProcesses.begin(),fListOfProcesses.end(),processName) != fListOfProcesses.end())){
    fTrackInformation  = G4Track(*(step->GetTrack()));
    fStepInformation = G4Step(*step);
    fTrackInformation.SetKineticEnergy(fStepInformation.GetPreStepPoint()->GetKineticEnergy());
    fTrackInformation.SetMomentumDirection(fStepInformation.GetPreStepPoint()->GetMomentumDirection());
    fTrackInformation.SetTrackStatus(fAlive);
    fTrackInformation.SetPolarization(fStepInformation.GetPreStepPoint()->GetPolarization());
    fProcessToSplit = processName;
    fIDOfSplittedTrack = step->GetTrack()->GetTrackID();
  }

}

void GateOptrLastVertexInteractionSplittingActor::CreateNewParticleAtTheLastVertex(G4Step* CurrentStep,G4Track track,G4Step step,G4String processName){
  G4ParticleDefinition* particleDefinition = track.GetDefinition();
  G4ProcessManager* processManager = particleDefinition->GetProcessManager();
  G4ProcessVector* processList = processManager->GetProcessList();
  auto processToSplit = (*processList)[0];
  for (size_t i = 0; i <processList->size(); ++i) {
    auto process = (*processList)[i];
    if (process->GetProcessName() == processName){
      processToSplit = process;
    }
  }

if (processName == "compt"){
  ComptonSplitting(CurrentStep,track,step,processToSplit,10);
}
else {
  std::cout<<processToSplit->GetProcessName()<<std::endl;
  SecondariesSplitting(CurrentStep,track,step,processToSplit,10);
}

}


void GateOptrLastVertexInteractionSplittingActor::BeginOfEventAction(const G4Event* event){
  fIDOfSplittedTrack = 0;
  fIsSplitted = false;
}



void GateOptrLastVertexInteractionSplittingActor::SteppingAction(G4Step* step) {
  G4int trackID  = step->GetTrack()->GetTrackID();
  if ((fIsSplitted == true) && ( trackID == fIDOfSplittedTrack - 1))
    fIsSplitted = false;

  if (fIsSplitted == false){
    RememberLastProcessInformation(step);
    G4String logicalVolumeNamePostStep = "None";
    if (step->GetPostStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(),logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()) {
      if (std::find(fListOfProcesses.begin(), fListOfProcesses.end(),fProcessToSplit) != fListOfProcesses.end()){
        CreateNewParticleAtTheLastVertex(step,fTrackInformation,fStepInformation,fProcessToSplit);
        fIsSplitted = true;
        fIDOfSplittedTrack = trackID;
        fProcessToSplit = "None";
      }
    }
  }
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......



//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
