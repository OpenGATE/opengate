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
  fBatchSize = DictGetDouble(user_info, "batch_size");
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

G4bool GateLastVertexInteractionSplittingActor::DoesParticleEmittedInSolidAngle(G4ThreeVector dir, G4ThreeVector vectorDirector) {
  G4double cosTheta = vectorDirector * dir;
  if (cosTheta < fCosMaxTheta)
    return false;
  return true;
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

G4Track* GateLastVertexInteractionSplittingActor::CreateATrackFromContainer(LastVertexDataContainer theContainer){

  auto *particle_table = G4ParticleTable::GetParticleTable();
  SimpleContainer container = theContainer.GetContainerToSplit();
  if (container.GetParticleNameToSplit() != "None"){
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
  
  return nullptr;


}


G4Track *GateLastVertexInteractionSplittingActor::CreateComptonTrack(G4ParticleChangeForGamma *gammaProcess, G4Track track, G4double weight) {
  
  G4double energy = gammaProcess->GetProposedKineticEnergy();
  G4double globalTime = track.GetGlobalTime();
  G4ThreeVector polarization = gammaProcess->GetProposedPolarization();
  const G4ThreeVector momentum = gammaProcess->GetProposedMomentumDirection();
  const G4ThreeVector position = track.GetPosition();
  G4Track *newTrack = new G4Track(track);

  newTrack->SetKineticEnergy(energy);
  newTrack->SetMomentumDirection(momentum);
  newTrack->SetPosition(position);
  newTrack->SetPolarization(polarization);
  newTrack->SetWeight(weight);
  return newTrack;
}

void GateLastVertexInteractionSplittingActor::ComptonSplitting(G4Step* initStep, G4Step *CurrentStep,G4VProcess *process, LastVertexDataContainer container, G4double batchSize) {

  //G4TrackVector *trackVector = CurrentStep->GetfSecondary();
  GateGammaEmPostStepDoIt *emProcess = (GateGammaEmPostStepDoIt *)process;
  for (int i = 0; i < batchSize; i++){
    G4VParticleChange *processFinalState = emProcess->PostStepDoIt(*fTrackToSplit, *initStep);
    G4ParticleChangeForGamma *gammaProcessFinalState = (G4ParticleChangeForGamma *)processFinalState;

    G4ThreeVector momentum = gammaProcessFinalState->GetProposedMomentumDirection();

    G4Track *newTrack = CreateComptonTrack(gammaProcessFinalState, *fTrackToSplit, fWeight);

    if ((fAngularKill) && (DoesParticleEmittedInSolidAngle(newTrack->GetMomentumDirection(),fVectorDirector) == false)){
      delete newTrack;
    }
    else{
      fStackManager->PushOneTrack(newTrack);
    }


    // Special case here, since we generate independently each particle, we will not attach an electron to exiting compton photon, but we will the secondaries.
    

    if (processFinalState->GetNumberOfSecondaries()> 0){
      delete processFinalState->GetSecondary(0);
    }

  
    processFinalState->Clear();
    gammaProcessFinalState->Clear();
  }
}




G4Track GateLastVertexInteractionSplittingActor::eBremProcessFinalState(G4Track* track, G4Step* step,G4VProcess *process){
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
  G4Track aTrack = G4Track(*track);

  aTrack.SetKineticEnergy(track->GetKineticEnergy() - LossEnergy);
  aTrack.SetMomentumDirection(momentum);
  aTrack.SetPolarization(polarization);
  eIoniProcessAlongState->Clear();
  eBremProcessAlongState->Clear();
  return aTrack;

}


void GateLastVertexInteractionSplittingActor::SecondariesSplitting(G4Step* initStep, G4Step *CurrentStep,G4VProcess *process,LastVertexDataContainer theContainer, G4double batchSize) {
  SimpleContainer container = theContainer.GetContainerToSplit();
  G4String particleName = fTrackToSplit->GetParticleDefinition()->GetParticleName();
  //G4TrackVector *trackVector = CurrentStep->GetfSecondary();

  G4VParticleChange *processFinalState = nullptr;
  GateBremPostStepDoIt* bremProcess = nullptr;
  GateGammaEmPostStepDoIt *emProcess = nullptr;
  GateplusannihilAtRestDoIt *eplusAnnihilProcess = nullptr;

  if ((container.GetAnnihilationFlag() == "PostStep") && (fTrackToSplit->GetKineticEnergy() > 0)){
    emProcess = (GateGammaEmPostStepDoIt *)process;
  }
  if ((container.GetAnnihilationFlag() == "AtRest") || (fTrackToSplit->GetKineticEnergy() == 0)) {
    eplusAnnihilProcess = (GateplusannihilAtRestDoIt *)process;
  }
  for (int j = 0; j < batchSize;j++){
    G4int NbOfSecondaries = 0;
    
    G4int count =0;
    while (NbOfSecondaries  == 0){
      if (process->GetProcessName() == "eBrem") {
        G4Track aTrack = eBremProcessFinalState(fTrackToSplit,initStep,process);
        bremProcess = (GateBremPostStepDoIt*) process;
        processFinalState = bremProcess->GateBremPostStepDoIt::PostStepDoIt(aTrack, *initStep);
      }
      else {
        if ((container.GetAnnihilationFlag() == "PostStep") && (fTrackToSplit->GetKineticEnergy() > 0)){
          processFinalState = emProcess->PostStepDoIt(*fTrackToSplit, *initStep);
        }
        if ((container.GetAnnihilationFlag() == "AtRest") || (fTrackToSplit->GetKineticEnergy() == 0)) {
          processFinalState = eplusAnnihilProcess->GateplusannihilAtRestDoIt::AtRestDoIt(*fTrackToSplit,*initStep);
        }
      }
      NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
      if (NbOfSecondaries == 0){
        processFinalState->Clear();
      }
      count ++;
      //Security break, in case of infinite loop
      if (count > 10000){
        G4ExceptionDescription ed;
        ed << " infinite loop detected during the track creation for the " <<process->GetProcessName() <<" process"<<G4endl;
        G4Exception("GateLastVertexInteractionSplittingActor::SecondariesSplitting","BIAS.LV1",JustWarning,ed);
        G4RunManager::GetRunManager()->AbortEvent();
        break;
      }
    }

    G4int idx = 0;
    G4bool IsPushBack =false;
    for (int i=0; i < NbOfSecondaries; i++){
      G4Track *newTrack = processFinalState->GetSecondary(i);
      G4ThreeVector momentum = newTrack->GetMomentumDirection();
      
      if (!(isnan(momentum[0]))){
        if ((fAngularKill) && (DoesParticleEmittedInSolidAngle(momentum,fVectorDirector) == false)){
          delete newTrack;
        }
        else if (IsPushBack == true){
          delete newTrack;
        }
        else {
          newTrack->SetWeight(fWeight);
          newTrack->SetCreatorProcess(process);
          //trackVector->emplace_back(newTrack);
          fStackManager->PushOneTrack(newTrack);
          //delete newTrack;
          IsPushBack=true;

        }
      }
      else {
        delete newTrack;
      }
    }
    processFinalState->Clear();
  }
}


void GateLastVertexInteractionSplittingActor::CreateNewParticleAtTheLastVertex(G4Step* initStep,G4Step *step,LastVertexDataContainer theContainer, G4double batchSize) {
  // We retrieve the process associated to the process name to split and we
  // split according the process. Since for compton scattering, the gamma is not
  // a secondary particles, this one need to have his own splitting function.

    G4String processName = fProcessNameToSplit;
    G4int nbOfTrackAlreadyInStack = fStackManager->GetNTotalTrack();
    if ((fProcessToSplit == 0) || (fProcessToSplit == nullptr)){
      SimpleContainer container = theContainer.GetContainerToSplit();
      fProcessToSplit = GetProcessFromProcessName(container.GetParticleNameToSplit(),processName);
    }
    
    if (processName == "compt") {
      ComptonSplitting(initStep,step, fProcessToSplit, theContainer, batchSize);
    }

    else if((processName != "msc") && (processName != "conv")){
      SecondariesSplitting(initStep, step, fProcessToSplit, theContainer,batchSize);
    }
    fNumberOfTrackToSimulate = fStackManager->GetNTotalTrack() - nbOfTrackAlreadyInStack;
    fNbOfBatchForExitingParticle ++;
    if (fNbOfBatchForExitingParticle >500){
      fStackManager->clear();
    }
    //stackManager->clear();

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
       if (processName == step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName()){
        annihilFlag = "PostStep";
      }
      else if (processName != step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName()){
        annihilFlag ="AtRest";
      }
    }
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
      container->PushListOfSplittingParameters(containerToSplit);
  
    }
  }


}



G4bool GateLastVertexInteractionSplittingActor::IsParticleExitTheBiasedVolume(G4Step*step){


  if ((step->GetPostStepPoint()->GetStepStatus() == 1)) {
    G4String logicalVolumeNamePostStep = "None";
    if (step->GetPostStepPoint()->GetPhysicalVolume() != 0)
        logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
    
    if (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(), logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()){
      return true;
    }
      /*
      else if (std::find(fListOfBiasedVolume.begin(), fListOfBiasedVolume.end(), logicalVolumeNamePostStep) != fListOfBiasedVolume.end()) {
        return false;
      }
      */
    }
  if (step->GetPostStepPoint()->GetStepStatus() == 0)
    return true;
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

G4bool GateLastVertexInteractionSplittingActor::IsTheParticleUndergoesALossEnergyProcess(G4Step* step){
  if (step->GetPostStepPoint()->GetKineticEnergy() - step->GetPreStepPoint()->GetKineticEnergy()  != 0)
    return true;
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

  fCosMaxTheta = std::cos(fMaxTheta);
  std::cout<<"batch size  "<<fBatchSize<<std::endl;
  fStackManager = G4EventManager::GetEventManager()->GetStackManager();
  
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
  fEventID = event->GetEventID();
  fIsAnnihilAlreadySplit = false;
  fNbOfBatchForExitingParticle = 0;
  if (fEventID%50000 == 0)
    std::cout<<"event ID : "<<fEventID<<std::endl;
  if (fCopyInitStep != 0){
    delete fCopyInitStep;
    fCopyInitStep = nullptr;
  }
  fSplitCounter =0;
  fNumberOfTrackToSimulate =0;
  fKilledBecauseOfProcess = false;

  if (fActiveSource == "source_vertex"){
    auto* source = fSourceManager->FindSourceByName(fActiveSource);
    GateLastVertexSource *vertexSource = (GateLastVertexSource*) source;
    fContainer = vertexSource->GetLastVertexContainer();
    fProcessNameToSplit = vertexSource->GetProcessToSplit();
    if (fProcessToSplit !=0){
      fProcessToSplit = nullptr;
    }
    if (fTrackToSplit !=0){
      delete fTrackToSplit;
      fTrackToSplit = nullptr;
    }
    fTrackToSplit = CreateATrackFromContainer(fContainer);
    if (fTrackToSplit != 0)
      fWeight = fTrackToSplit->GetWeight()/fSplittingFactor;
  }


}

void GateLastVertexInteractionSplittingActor::PreUserTrackingAction(
    const G4Track *track) {
      fToSplit =true;
      fIsFirstStep = true;
  
}

void GateLastVertexInteractionSplittingActor::SteppingAction(G4Step *step) {
 

  if (fActiveSource != "source_vertex"){
    FillOfDataTree(step);
    
    if (IsParticleExitTheBiasedVolume(step)){
      if ((fAngularKill == false) ||  ((fAngularKill == true) && (DoesParticleEmittedInSolidAngle(step->GetTrack()->GetMomentumDirection(),fVectorDirector) == true))){
        fListOfContainer.push_back((*fIterator));
      }
      
      step->GetTrack()->SetTrackStatus(fStopAndKill);
    }
    
    
  }

 

  if (fOnlyTree == false){
    if (fActiveSource == "source_vertex"){

      if (fIsFirstStep){
        fTrackID = step->GetTrack()->GetTrackID();
        fEkin = step->GetPostStepPoint()->GetKineticEnergy();
      }
      else{
        if ((fTrackID == step->GetTrack()->GetTrackID()) && (fEkin != step->GetPreStepPoint()->GetKineticEnergy())){
          fToSplit =false;
        }
        else{
          fEkin = step->GetPostStepPoint()->GetKineticEnergy();
        }

      }
      if (fToSplit) {
        G4String creatorProcessName = "None";
        if (step->GetTrack()->GetCreatorProcess() != 0)
          creatorProcessName =step->GetTrack()->GetCreatorProcess()->GetProcessName();
        if (((step->GetTrack()->GetParentID() == 0)&&  (step->GetTrack()->GetTrackID() == 1))|| ((creatorProcessName == "annihil") && (step->GetTrack()->GetParentID() == 1))){

          if ((fProcessNameToSplit != "annihil") || ((fProcessNameToSplit == "annihil")&& (fIsAnnihilAlreadySplit ==false))){
            
            //FIXME : list of process which are not splitable yet
            if ((fProcessNameToSplit != "msc") && (fProcessNameToSplit != "conv") && (fProcessNameToSplit != "eIoni")) {
              fCopyInitStep = new G4Step(*step);
              if (fProcessNameToSplit  == "eBrem"){
                fCopyInitStep->SetStepLength(fContainer.GetContainerToSplit().GetStepLength());
                fCopyInitStep->GetPreStepPoint()->SetKineticEnergy(fContainer.GetContainerToSplit().GetEnergy());

              }
              CreateNewParticleAtTheLastVertex(fCopyInitStep,step,fContainer, fBatchSize);
            }
            step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
            
            if (fProcessNameToSplit == "annihil"){
              fIsAnnihilAlreadySplit = true;
              }
            }


          else if ((fProcessNameToSplit == "annihil")&& (fIsAnnihilAlreadySplit == true)){
            step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
          }
          
          }
        
        else {
          if (fIsFirstStep){
            fNumberOfTrackToSimulate --;
            if (fKilledBecauseOfProcess == false){
              fSplitCounter += 1;
            }
            else {
              fKilledBecauseOfProcess = false;
            }

            if (fSplitCounter > fSplittingFactor){
              step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
              fStackManager->clear();
            }
          }

          if (IsTheParticleUndergoesALossEnergyProcess(step)){
            step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
            fKilledBecauseOfProcess = true;
          }

          if (fIsFirstStep){
             if (fSplitCounter <= fSplittingFactor){
                if (fNumberOfTrackToSimulate == 0){
                  CreateNewParticleAtTheLastVertex(fCopyInitStep,step,fContainer,(fSplittingFactor - fSplitCounter +1)/fSplittingFactor * fBatchSize);
                }
            }
          }
        }
      }    
    }
  }

  fIsFirstStep = false;



  
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
