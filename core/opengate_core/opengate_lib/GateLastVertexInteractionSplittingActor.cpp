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
/// \file GateLastVertexInteractionSplittingActor.cc
/// \brief Implementation of the GateLastVertexInteractionSplittingActor class

#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "CLHEP/Units/SystemOfUnits.h"
#include "G4BiasingProcessInterface.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4Positron.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "G4TrackStatus.hh"
#include "G4TrackingManager.hh"
#include "G4VParticleChange.hh"
#include "G4eplusAnnihilation.hh"
#include "GateLastVertexInteractionSplittingActor.h"
#include "GateLastVertexSplittingPostStepDoIt.h"
#include "GateOptnComptSplitting.h"
#include "GateLastVertexSource.h"
#include "G4RunManager.hh"
#include <cmath>


//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateLastVertexInteractionSplittingActor::
    GateLastVertexInteractionSplittingActor(py::dict &user_info)
    : GateVActor(user_info, false) {
  fMotherVolumeName = DictGetStr(user_info, "mother");
  fSplittingFactor = DictGetDouble(user_info, "splitting_factor");
  fRotationVectorDirector = DictGetBool(user_info, "rotation_vector_director");
  fAngularKill = DictGetBool(user_info, "angular_kill");
  fVectorDirector = DictGetG4ThreeVector(user_info, "vector_director");
  fMaxTheta = DictGetDouble(user_info, "max_theta");
  fActions.insert("StartSimulationAction");
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("PostUserTrackingAction");
  fActions.insert("EndOfEventAction");
  
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void GateLastVertexInteractionSplittingActor::print_tree(const tree<LastVertexDataContainer>& tr, tree<LastVertexDataContainer>::pre_order_iterator it, tree<LastVertexDataContainer>::pre_order_iterator end)
	{
	if(!tr.is_valid(it)) return;
	int rootdepth=tr.depth(it);
	std::cout << "-----" << std::endl;
	while(it!=end) {
		for(int i=0; i<tr.depth(it)-rootdepth; ++i) 
			std::cout << "  ";
		std::cout << (*it) << std::endl << std::flush;
		++it;
		}
	std::cout << "-----" << std::endl;
	}


G4bool GateLastVertexInteractionSplittingActor::DoesParticleEmittedInSolidAngle(G4ThreeVector dir, G4ThreeVector vectorDirector, G4double maxTheta) {
  G4double cosTheta = vectorDirector * dir;
  G4double theta = std::acos(cosTheta);
  if (theta > fMaxTheta)
    return false;
  return true;
}


G4Track* GateLastVertexInteractionSplittingActor::CreateATrackFromContainer(LastVertexDataContainer theContainer, G4Step *step ){
  auto *particle_table = G4ParticleTable::GetParticleTable();
  SimpleContainer container = theContainer.GetContainerToSplit();
  G4ParticleDefinition *particleDefinition = particle_table->FindParticle(container.GetParticleNameToSplit());
  G4ThreeVector momentum = container.GetMomentum();
  G4double energy = container.GetEnergy();
  if (energy <0){
    energy = 0;
    momentum = {0,0,0};
  }
  G4int trackStatus = container.GetTrackStatus();
  G4ThreeVector position = container.GetVertexPosition();
  G4ThreeVector polarization = container.GetPolarization();

  G4DynamicParticle* dynamicParticle = new G4DynamicParticle(particleDefinition,momentum,energy);
  G4double time = 0;
  if (step->GetPreStepPoint() != 0)
    time = step->GetPreStepPoint()->GetGlobalTime();
  G4Track* aTrack = new G4Track(dynamicParticle,time, position);
  aTrack->SetPolarization(polarization);
  if (trackStatus == 0){
    aTrack->SetTrackStatus(fAlive);
  }
  if (trackStatus == 1){
    aTrack->SetTrackStatus(fStopButAlive);
  }
  if ((trackStatus == 2) || (trackStatus == 3)){
    aTrack->SetTrackStatus(fAlive);
  }
  aTrack->SetWeight(container.GetWeight());
  
  return aTrack;


}


G4Track *GateLastVertexInteractionSplittingActor::CreateComptonTrack(G4ParticleChangeForGamma *gammaProcess, G4Track track, G4double weight) {
  
  G4double energy = gammaProcess->GetProposedKineticEnergy();
  G4double globalTime = track.GetGlobalTime();
  //G4double newGammaWeight = weight;
  G4ThreeVector polarization = gammaProcess->GetProposedPolarization();
  const G4ThreeVector momentum = gammaProcess->GetProposedMomentumDirection();
  const G4ThreeVector position = track.GetPosition();
  G4Track *newTrack = new G4Track(track);

  //newTrack->SetWeight(newGammaWeight);
  newTrack->SetKineticEnergy(energy);
  newTrack->SetMomentumDirection(momentum);
  newTrack->SetPosition(position);
  newTrack->SetPolarization(polarization);
  return newTrack;
}

void GateLastVertexInteractionSplittingActor::ComptonSplitting(G4Step* initStep, G4Step *CurrentStep,G4VProcess *process, LastVertexDataContainer container) {

  G4TrackVector *trackVector = CurrentStep->GetfSecondary();
  G4double gammaWeight = 0;

  G4Track* aTrack = CreateATrackFromContainer(container,initStep);

  GateGammaEmPostStepDoIt *emProcess = (GateGammaEmPostStepDoIt *)process;
  G4VParticleChange *processFinalState = emProcess->PostStepDoIt(*aTrack, *initStep);
  G4ParticleChangeForGamma *gammaProcessFinalState = (G4ParticleChangeForGamma *)processFinalState;

  const G4ThreeVector momentum = gammaProcessFinalState->GetProposedMomentumDirection();
  //gammaWeight = aTrack->GetWeight()/ fSplittingFactor;

  
  G4Track *newTrack = CreateComptonTrack(gammaProcessFinalState, *aTrack, gammaWeight);

  if ((fAngularKill) && (DoesParticleEmittedInSolidAngle(newTrack->GetMomentumDirection(),fVectorDirector,fMaxTheta) == false))
    delete newTrack; 
  else {
    trackVector->push_back(newTrack);
    G4int NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
    for (int j = 0; j < NbOfSecondaries; j++) {
      G4Track *newTrack = processFinalState->GetSecondary(j);
      //newTrack->SetWeight(gammaWeight);
      trackVector->push_back(newTrack);
    }
  }

  processFinalState->Clear();
  gammaProcessFinalState->Clear();
  delete aTrack;


    
   
}



G4VProcess* GateLastVertexInteractionSplittingActor::GetProcessFromProcessName(G4String particleName, G4String pName){
  auto *particle_table = G4ParticleTable::GetParticleTable();  
  G4ParticleDefinition *particleDefinition = particle_table->FindParticle(particleName);
  G4ProcessManager *processManager = particleDefinition->GetProcessManager();
  G4ProcessVector *processList = processManager->GetProcessList();
  G4VProcess* nullProcess = nullptr;
  for (size_t i = 0; i < processList->size(); ++i) {
    auto process = (*processList)[i];
    if (process->GetProcessName() == pName) {
      return process;
    }
  }
  return nullProcess;

}


G4VParticleChange* GateLastVertexInteractionSplittingActor::eBremProcessFinalState(G4Track* track, G4Step* step,G4VProcess *process){
  //It seem's that the the along step method apply only to brem results to no deposited energy but a change in momentum direction according to the process
  //Whereas the along step method applied to the ionisation well change the deposited energy but not the momentum. Then I apply both to have a correct
  //momentum and deposited energy before the brem effect.
  G4String particleName = track->GetDefinition()->GetParticleName();
  G4VProcess* eIoniProcess = GetProcessFromProcessName(particleName, "eIoni");
  G4VProcess* eBremProcess = GetProcessFromProcessName(particleName, "eBrem");
  G4VParticleChange* eIoniProcessAlongState = eIoniProcess->AlongStepDoIt(*track, *step);
  G4VParticleChange* eBremProcessAlongState = eBremProcess->AlongStepDoIt(*track, *step);
  G4ParticleChangeForLoss* eIoniProcessAlongStateForLoss =   (G4ParticleChangeForLoss*) eIoniProcessAlongState;
  G4ParticleChangeForLoss* eBremProcessAlongStateForLoss =   (G4ParticleChangeForLoss*) eBremProcessAlongState;
  G4double LossEnergy = eIoniProcessAlongStateForLoss->GetLocalEnergyDeposit();
  G4ThreeVector momentum =  eBremProcessAlongStateForLoss->GetProposedMomentumDirection();
  G4ThreeVector polarization = eBremProcessAlongStateForLoss->GetProposedPolarization();

  track->SetKineticEnergy(track->GetKineticEnergy() - LossEnergy);
  track->SetMomentumDirection(momentum);
  track->SetPolarization(polarization);
  GateBremPostStepDoIt *bremProcess = (GateBremPostStepDoIt *)process;
  eIoniProcessAlongState->Clear();
  eBremProcessAlongState->Clear();

  return bremProcess->GateBremPostStepDoIt::PostStepDoIt(*track, *step);

}


void GateLastVertexInteractionSplittingActor::SecondariesSplitting(G4Step* initStep, G4Step *CurrentStep,G4VProcess *process,LastVertexDataContainer theContainer) {

    
  G4Track* track = CreateATrackFromContainer(theContainer,initStep);
  SimpleContainer container = theContainer.GetContainerToSplit();
  G4String particleName = track->GetParticleDefinition()->GetParticleName();
  G4TrackVector *trackVector = CurrentStep->GetfSecondary();
  G4double gammaWeight = 0;
  G4VParticleChange *processFinalState = nullptr;
  if (process->GetProcessName() == "eBrem") {
    processFinalState = eBremProcessFinalState(track,initStep,process);
  } 
  else {
    GateGammaEmPostStepDoIt *emProcess = (GateGammaEmPostStepDoIt *)process;
    if ((container.GetAnnihilationFlag() == "PostStep") && (track->GetKineticEnergy() > 0)){
      processFinalState = emProcess->PostStepDoIt(*track, *initStep);
    }
    if ((container.GetAnnihilationFlag() == "AtRest") || (track->GetKineticEnergy() == 0)) {
      GateplusannihilAtRestDoIt *eplusAnnihilProcess = (GateplusannihilAtRestDoIt *)process;
      processFinalState = eplusAnnihilProcess->GateplusannihilAtRestDoIt::AtRestDoIt(*track,*initStep);
    }
  }


  
  G4int NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
  G4int idx = 0;
  if (NbOfSecondaries >0) {
    //gammaWeight = track->GetWeight()/fSplittingFactor;
    G4bool alreadySplitted = false;
    for (int i; i < NbOfSecondaries; i++){
      G4Track *newTrack = processFinalState->GetSecondary(i);
      G4ThreeVector momentum = newTrack->GetMomentumDirection();
      if (!(isnan(momentum[0]))){
        if ((fAngularKill) && (DoesParticleEmittedInSolidAngle(momentum,fVectorDirector,fMaxTheta) == false)){
          delete newTrack;
        }
        else if (alreadySplitted == false){
          //newTrack->SetWeight(gammaWeight);
          newTrack->SetCreatorProcess(process);
          trackVector->push_back(newTrack);
          alreadySplitted = true;
        }
        else{
          delete newTrack;
        }
      }
      else {
        delete newTrack;
      }
    }
  }

  delete track;
  
  


  processFinalState->Clear();


}


void GateLastVertexInteractionSplittingActor::CreateNewParticleAtTheLastVertex(G4Step* initStep,G4Step *step,LastVertexDataContainer theContainer) {
  // We retrieve the process associated to the process name to split and we
  // split according the process. Since for compton scattering, the gamma is not
  // a secondary particles, this one need to have his own splitting function.
  SimpleContainer container = theContainer.GetContainerToSplit();
  G4VProcess* processToSplit = GetProcessFromProcessName(container.GetParticleNameToSplit(),container.GetProcessNameToSplit());
  G4String processName = container.GetProcessNameToSplit();
  if (processName == "compt") {
    ComptonSplitting(initStep,step, processToSplit, theContainer);
  }

  else if((processName != "msc") && (processName != "conv")){
    SecondariesSplitting(initStep, step, processToSplit, theContainer);
  }
  
}


void GateLastVertexInteractionSplittingActor::CreateListOfbiasedVolume(G4LogicalVolume *volume) {
  G4int nbOfDaughters = volume->GetNoDaughters();
  if (nbOfDaughters > 0) {
    for (int i = 0; i < nbOfDaughters; i++) {
      G4String LogicalVolumeName = volume->GetDaughter(i)->GetLogicalVolume()->GetName();
      G4LogicalVolume *logicalDaughtersVolume = volume->GetDaughter(i)->GetLogicalVolume();
      if (!(std::find(fListOfBiasedVolume.begin(),fListOfBiasedVolume.end(),LogicalVolumeName) != fListOfBiasedVolume.end()))
        fListOfBiasedVolume.push_back(volume->GetDaughter(i)->GetLogicalVolume()->GetName());
      CreateListOfbiasedVolume(logicalDaughtersVolume);
    }
  }
}


void GateLastVertexInteractionSplittingActor::FillOfDataTree(G4Step*step){

  G4String processName = "None";
  if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0)
      processName = step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName();
    
  G4String creatorProcessName = "None";
  if (step->GetTrack()->GetCreatorProcess() != 0)
    creatorProcessName =step->GetTrack()->GetCreatorProcess()->GetProcessName();
  
  if ((step->GetTrack()->GetParticleDefinition()->GetParticleName() == "e+") &&
      ((step->GetTrack()->GetTrackStatus() == 1) ||
       (step->GetTrack()->GetTrackStatus() == 2))) {
    processName = "annihil";
  }

  G4String annihilFlag = "None";
  if (processName == "annihil"){
    if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0){
      //std::cout<<processName<<"   "<<step->GetPreStepPoint()->GetKineticEnergy()<<"   "<<step->GetPostStepPoint()->GetKineticEnergy()<<"  "<<step->GetTotalEnergyDeposit()<<std::endl;
      if (processName == step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName()){
        annihilFlag = "PostStep";
      }
      else if (processName != step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName()){
        annihilFlag ="AtRest";
      }
      //std::cout<<annihilFlag<<std::endl;
    }
  }

  
  if (processName =="eBrem"){
    //std:cout<<step->GetPreStepPoint()->GetKineticEnergy()<<"   "<<step->GetPostStepPoint()->GetKineticEnergy()<<"  "<<step->GetTotalEnergyDeposit()<<std::endl;
  }
  

  if (fIsFirstStep){
    LastVertexDataContainer newContainer = LastVertexDataContainer();
    newContainer.SetTrackID(step->GetTrack()->GetTrackID());
    newContainer.SetParticleName(step->GetTrack()->GetDefinition()->GetParticleName());
    newContainer.SetCreationProcessName(creatorProcessName);
    if (fTree.empty()){  
      fTree.set_head(newContainer);
    }
      
    for (auto it = fTree.begin_post(); it != fTree.end_post(); ++it){
      LastVertexDataContainer container = *it;
      G4int trackID = container.GetTrackID();
      
      if (step->GetTrack()->GetParentID() == trackID){
        newContainer = container.ContainerFromParentInformation(step);
        fTree.append_child(it,newContainer);
          break;

      }
    }

    for (auto it = fTree.begin_post(); it != fTree.end_post(); ++it){
      LastVertexDataContainer container = *it;
      G4int trackID = container.GetTrackID();
      if (step->GetTrack()->GetTrackID() == trackID){
        fIterator = it;
        break;
      }
    }
  }

    LastVertexDataContainer* container = &(*fIterator);
    G4int trackID = container->GetTrackID();
    if ((processName != "Transportation") &&(processName !="None") && (processName !="Rayl")){
      if (step->GetTrack()->GetTrackID() == trackID){
        G4ThreeVector position = step->GetTrack()->GetPosition();
        G4ThreeVector prePosition = step->GetPreStepPoint()->GetPosition();
        G4ThreeVector momentum;
        if ((processName == "annihil")) 
          momentum = step->GetPostStepPoint()->GetMomentumDirection();
        else{
          momentum = step->GetPreStepPoint()->GetMomentumDirection();
        }
        G4ThreeVector polarization = step->GetPreStepPoint()->GetPolarization();
        G4String particleName = step->GetTrack()->GetDefinition()->GetParticleName();
        G4double energy = step->GetPreStepPoint()->GetKineticEnergy();
        G4double weight = step->GetTrack()->GetWeight();
        G4int trackStatus = step->GetTrack()->GetTrackStatus();
        G4int nbOfSecondaries = step->GetfSecondary()->size();
        G4double stepLength = step->GetStepLength();
        if (((processName == "annihil"))){
          energy -= (step->GetTotalEnergyDeposit());
        }
        SimpleContainer containerToSplit = SimpleContainer(processName,energy, momentum, position,polarization,particleName,weight,trackStatus,nbOfSecondaries,annihilFlag,stepLength,prePosition);
        container->SetContainerToSplit(containerToSplit);
        container->PushListOfSplittingParameters();
    
      }
    }
}



G4bool GateLastVertexInteractionSplittingActor::IsParticleExitTheBiasedVolume(G4Step*step){
  G4String logicalVolumeNamePreStep = "None";
  G4String logicalVolumeNamePostStep = "None";
  if (step->GetPreStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePreStep = step->GetPreStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
  if (step->GetPostStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
  

  if (logicalVolumeNamePreStep != logicalVolumeNamePostStep){
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(), logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()){
      return true;
    }
    /*
    else if (std::find(fListOfBiasedVolume.begin(), fListOfBiasedVolume.end(), logicalVolumeNamePostStep) != fListOfBiasedVolume.end()) {
      return false;
    }
    */
  }
  return false;
}



G4bool GateLastVertexInteractionSplittingActor::IsTheParticleUndergoesAProcess(G4Step* step){
  G4String processName = "None";
  G4String particleName = step->GetTrack()->GetParticleDefinition()->GetParticleName();
  if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0)
    processName = step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName();
  
  if (std::find(fListOfProcessesAccordingParticles[particleName].begin(), fListOfProcessesAccordingParticles[particleName].end(), processName) != fListOfProcessesAccordingParticles[particleName].end()){
    return true;
  }
  return false;


}


void GateLastVertexInteractionSplittingActor::StartSimulationAction (){
  fListOfProcessesAccordingParticles["gamma"] = {"compt","phot","conv"};
  fListOfProcessesAccordingParticles["e-"] = {"eBrem","eIoni","msc"};
  fListOfProcessesAccordingParticles["e+"] = {"eBrem","eIoni","msc","annihil"};


  G4LogicalVolume *biasingVolume = G4LogicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);
  fListOfBiasedVolume.push_back(biasingVolume->GetName());
  CreateListOfbiasedVolume(biasingVolume);

  auto* source  = fSourceManager->FindSourceByName("source_vertex");
  fVertexSource = (GateLastVertexSource* ) source;
}


void GateLastVertexInteractionSplittingActor::BeginOfRunAction(
    const G4Run *run) {

  if (fRotationVectorDirector) {
    G4VPhysicalVolume *physBiasingVolume =
        G4PhysicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);
    auto rot = physBiasingVolume->GetObjectRotationValue();
    fVectorDirector = rot * fVectorDirector;
  }
}

void GateLastVertexInteractionSplittingActor::BeginOfEventAction(
    const G4Event *event) {
  fParentID = -1;
  fEventID = event->GetEventID();
  fEventIDOfSplittedTrack = -1;
  fTrackIDOfSplittedTrack = -1;
  fNotSplitted == true;
  fIsAnnihilAlreadySplit = false;
  if (fEventID%50000 == 0)
    std::cout<<fEventID<<std::endl;
  fCopyInitStep = nullptr;



}

void GateLastVertexInteractionSplittingActor::PreUserTrackingAction(
    const G4Track *track) {
      
      fIsFirstStep = true;
  
}

void GateLastVertexInteractionSplittingActor::SteppingAction(G4Step *step) {
 

  G4String logicalVolumeNamePreStep = "None";
  G4String logicalVolumeNamePostStep = "None";
 
  if (step->GetPreStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePreStep = step->GetPreStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
  if (step->GetPostStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();

  G4String particleName =step->GetTrack()->GetParticleDefinition()->GetParticleName();
  G4String creatorProcessName = "None";
  G4String processName = "None";

  if (step->GetTrack()->GetCreatorProcess() != 0)
    creatorProcessName =step->GetTrack()->GetCreatorProcess()->GetProcessName();
  
  if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0)
    processName = step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName();

  
  if (fActiveSource != "source_vertex"){
    FillOfDataTree(step);
    if (IsParticleExitTheBiasedVolume(step)){
      if ((fAngularKill == false) ||  ((fAngularKill == true) && (DoesParticleEmittedInSolidAngle(step->GetTrack()->GetMomentumDirection(),fVectorDirector,fMaxTheta) == true))){
        fListOfContainer.push_back((*fIterator));
      }
      step->GetTrack()->SetTrackStatus(fStopAndKill);
    }
  }


  if (fOnlyTree == false){
    if (fActiveSource == "source_vertex"){
    
      auto* source = fSourceManager->FindSourceByName(fActiveSource);
      GateLastVertexSource *vertexSource = (GateLastVertexSource*) source;
      LastVertexDataContainer container = vertexSource->GetLastVertexContainer();
      if ((step->GetTrack()->GetWeight() == container.GetContainerToSplit().GetWeight())){
        G4ThreeVector momentum = step->GetPreStepPoint()->GetMomentumDirection();
        G4String processToSplit = vertexSource->GetProcessToSplit();
        if (((step->GetTrack()->GetParentID() == 0)&&  (step->GetTrack()->GetTrackID() == 1))|| ((creatorProcessName == "annihil") && (step->GetTrack()->GetParentID() == 1))){

          if ((processToSplit != "annihil") || ((processToSplit == "annihil")&& (fIsAnnihilAlreadySplit ==false))){

            step->GetfSecondary()->clear();
            //FIXME : list of process which are not splitable yet
            if ((processToSplit != "msc") && (processToSplit != "conv") && (processToSplit != "eIoni")) {
              fCopyInitStep= new G4Step(*step);
              if (processToSplit  == "eBrem"){
                fCopyInitStep->SetStepLength(container.GetContainerToSplit().GetStepLength());
                fCopyInitStep->GetPreStepPoint()->SetKineticEnergy(container.GetContainerToSplit().GetEnergy());

              }
              while (step->GetfSecondary()->size() != 1){
                step->GetfSecondary()->clear();
                CreateNewParticleAtTheLastVertex(fCopyInitStep,step,container);

              }
            }
            step->GetTrack()->SetTrackStatus(fStopAndKill);
            
            if (processToSplit == "annihil"){
              fIsAnnihilAlreadySplit = true;
              }
            }


          else if ((processToSplit == "annihil")&& (fIsAnnihilAlreadySplit == true)){
            step->GetfSecondary()->clear();
            step->GetTrack()->SetTrackStatus(fStopAndKill);
          }
          
          }

        
        else if (IsTheParticleUndergoesAProcess(step)){
          step->GetfSecondary()->clear();
          while (step->GetfSecondary()->size() != 1){
                step->GetfSecondary()->clear();
                CreateNewParticleAtTheLastVertex(fCopyInitStep,step,container);
              }
          step->GetTrack()->SetTrackStatus(fStopAndKill);
          
        }
        

        else if (IsParticleExitTheBiasedVolume(step)){
          fSplitCounter += 1;
          if (fSplitCounter < fSplittingFactor){
            while (step->GetfSecondary()->size() != 1){
                step->GetfSecondary()->clear();
                CreateNewParticleAtTheLastVertex(fCopyInitStep,step,container);

              }
          }
          else{
            delete fCopyInitStep;
            fCopyInitStep = nullptr;
            fSplitCounter = 0;
          }
          

          //FIXME Debug case if splitting factor equal to 1, as It is used as a condition to enable the split
          // I just set the weight to a very close value of the real one
          if (fSplittingFactor != 1)
            step->GetPostStepPoint()->SetWeight(container.GetContainerToSplit().GetWeight()/fSplittingFactor);
          else
            step->GetPostStepPoint()->SetWeight(container.GetContainerToSplit().GetWeight()*0.99999999);
        }   
      }
    }
  }

  fIsFirstStep = false;



  
}

void GateLastVertexInteractionSplittingActor::PostUserTrackingAction(
    const G4Track *track) {

    }


void GateLastVertexInteractionSplittingActor::EndOfEventAction(
    const G4Event* event) {


      if (fActiveSource != "source_vertex"){
        //print_tree(fTree,fTree.begin(),fTree.end());
        fVertexSource->SetNumberOfEventToSimulate(fListOfContainer.size());
        fVertexSource->SetNumberOfGeneratedEvent(0);
        fVertexSource->SetListOfVertexToSimulate(fListOfContainer);
        fTree.clear();
        fListOfContainer.clear();
      }

      if (fOnlyTree == false){

      auto* source = fSourceManager->FindSourceByName("source_vertex");
      GateLastVertexSource* vertexSource = (GateLastVertexSource*) source;
      if (vertexSource->GetNumberOfGeneratedEvent() < vertexSource->GetNumberOfEventToSimulate()){
        fSourceManager->SetActiveSourcebyName("source_vertex");
      }
      fActiveSource = fSourceManager->GetActiveSourceName();
      }
      
    }

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
