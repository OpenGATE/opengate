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
#include "G4Positron.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4ProcessManager.hh"
#include "G4TrackingManager.hh"
#include "G4TrackStatus.hh"
#include "G4ProcessVector.hh"
#include "GateOptnComptSplitting.h"
#include "GateLastVertexInteractionSplittingActor.h"
#include "GateLastVertexSplittingPostStepDoIt.h"
#include "G4VParticleChange.hh"
#include "G4eplusAnnihilation.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateLastVertexInteractionSplittingActor::GateLastVertexInteractionSplittingActor(py::dict &user_info) : GateVActor(user_info, false)
{
  fMotherVolumeName = DictGetStr(user_info, "mother");
  fSplittingFactor = DictGetDouble(user_info, "splitting_factor");
  fRotationVectorDirector = DictGetBool(user_info, "rotation_vector_director");
  fRussianRouletteForAngle = DictGetBool(user_info, "russian_roulette_for_angle");
  fVectorDirector = DictGetG4ThreeVector(user_info, "vector_director");
  fMaxTheta = DictGetDouble(user_info, "max_theta");
  fActions.insert("StartSimulationAction");
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("PostUserTrackingAction");
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4double GateLastVertexInteractionSplittingActor::RussianRouletteForAngleSurvival(G4ThreeVector dir, G4ThreeVector vectorDirector, G4double maxTheta, G4double split)
{
  G4double cosTheta = vectorDirector * dir;
  G4double theta = std::acos(cosTheta);
  G4double weightToApply = 1;
  if (theta > fMaxTheta)
  {
    G4double probability = G4UniformRand();
    if (probability <= 1 / split)
    {
      weightToApply = split;
    }
    else
    {
      weightToApply = 0;
    }
  }
  return weightToApply;
}

G4Track *GateLastVertexInteractionSplittingActor::CreateComptonTrack(G4ParticleChangeForGamma *gammaProcess, G4Track track, G4double weight)
{
  G4double energy = gammaProcess->GetProposedKineticEnergy();
  G4double globalTime = track.GetGlobalTime();
  G4double newGammaWeight = weight;
  G4ThreeVector polarization = gammaProcess->GetProposedPolarization(); 
  const G4ThreeVector momentum = gammaProcess->GetProposedMomentumDirection();
  const G4ThreeVector position = track.GetPosition();
  G4Track *newTrack = new G4Track(track);

  newTrack->SetWeight(newGammaWeight);
  newTrack->SetKineticEnergy(energy);
  newTrack->SetMomentumDirection(momentum);
  newTrack->SetPosition(position);
  newTrack->SetPolarization(polarization);
  return newTrack;
}

void GateLastVertexInteractionSplittingActor::ComptonSplitting(G4Step *CurrentStep, G4Track *track, const G4Step *step, G4VProcess *process)
{
  // Loop on process and add the secondary tracks to the current step secondary vector

  G4TrackVector *trackVector = CurrentStep->GetfSecondary();
  G4double gammaWeight = 0;

  GateGammaEmPostStepDoIt *emProcess = (GateGammaEmPostStepDoIt *)process;
  G4VParticleChange *processFinalState = emProcess->PostStepDoIt(*track, *step);
  G4ParticleChangeForGamma *gammaProcessFinalState = (G4ParticleChangeForGamma *)processFinalState;
  const G4ThreeVector momentum = gammaProcessFinalState->GetProposedMomentumDirection();
  gammaWeight = fWeightOfEnteringParticle/ fSplittingFactor;
  if (fRussianRouletteForAngle == true)
  {
    G4double weightToApply = RussianRouletteForAngleSurvival(momentum, fVectorDirector, fMaxTheta, fSplittingFactor);
    if (weightToApply != 0)
    {
      gammaWeight = gammaWeight * weightToApply;
      G4Track *newTrack = CreateComptonTrack(gammaProcessFinalState, *track, gammaWeight);
      trackVector->push_back(newTrack);
      G4int NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
      for (int j = 0; j < NbOfSecondaries; j++)
      {
        G4Track *newTrack = processFinalState->GetSecondary(j);
        newTrack->SetWeight(gammaWeight);
        trackVector->push_back(newTrack);
      }
    }
  }

  else
  {
    G4Track *newTrack = CreateComptonTrack(gammaProcessFinalState, *track, gammaWeight);
    trackVector->push_back(newTrack);
    G4int NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
    for (int j = 0; j < NbOfSecondaries; j++)
    {
      G4Track *newTrack = processFinalState->GetSecondary(j);
      newTrack->SetWeight(gammaWeight);
      trackVector->push_back(newTrack);
    }
  }
  processFinalState->Clear();
  gammaProcessFinalState->Clear();
  

}

void GateLastVertexInteractionSplittingActor::SecondariesSplitting(G4Step *CurrentStep, G4Track* track, const G4Step *step, G4VProcess *process)
{
  // Loop on process and add the secondary tracks to the current step secondary vector.

  //std::cout<<track->GetKineticEnergy()<<"   "<<track->GetDynamicParticle()->GetKineticEnergy()<<"   "<<track->GetMomentumDirection()<<"       "<<track->GetDynamicParticle()->GetMomentumDirection()<<std::endl;

  G4String particleName = track->GetParticleDefinition()->GetParticleName();
  G4TrackVector *trackVector = CurrentStep->GetfSecondary();
  G4double gammaWeight = 0;  
  G4VParticleChange *processFinalState = nullptr;
  if (process->GetProcessName() == "eBrem")
  {
    GateBremPostStepDoIt *bremProcess = (GateBremPostStepDoIt *)process;
    processFinalState = bremProcess->GateBremPostStepDoIt::PostStepDoIt(*track, *step);
  }
  else
  {
    GateGammaEmPostStepDoIt *emProcess = (GateGammaEmPostStepDoIt *) process ;
    if (track->GetTrackStatus() == 0){
      //if (process->GetProcessName() == "annihil")
        //std::cout<<"lol"<<std::endl;
      processFinalState = emProcess->PostStepDoIt(*track, *step);
    }
    if (track->GetTrackStatus() == 1){
      GateplusannihilAtRestDoIt* eplusAnnihilProcess  = (GateplusannihilAtRestDoIt*) process;

      processFinalState = eplusAnnihilProcess ->GateplusannihilAtRestDoIt::AtRestDoIt(*track, *step);
    }
  }
  
  
  G4int NbOfSecondaries = processFinalState->GetNumberOfSecondaries();
  
  if (NbOfSecondaries > 0) {
    gammaWeight =  fWeightOfEnteringParticle/fSplittingFactor;
    G4Track *newTrack = processFinalState->GetSecondary(0);
    if ((fRussianRouletteForAngle == true) && (particleName == "gamma"))
    {
      const G4ThreeVector momentum = newTrack->GetMomentumDirection();
      G4double weightToApply = RussianRouletteForAngleSurvival(momentum, fVectorDirector, fMaxTheta, fSplittingFactor);
      if (weightToApply != 0)
      {
        gammaWeight = gammaWeight * weightToApply;
        newTrack->SetWeight(gammaWeight);
        trackVector->push_back(newTrack);
      }
    }
    else
    {
      newTrack->SetWeight(gammaWeight);
      trackVector->push_back(newTrack);
    }
  }
  else {
    processFinalState->Clear();
    SecondariesSplitting(CurrentStep,track, step, process);
  }
  processFinalState->Clear();

}

void GateLastVertexInteractionSplittingActor::ClearRememberedTracksAndSteps(std::map<G4int, G4TrackVector> rememberedTracks, std::map<G4int, std::vector<G4Step *>> rememberedSteps)
{
  std::vector<G4Track*> trackToKill = {};
  for (auto it = rememberedTracks.begin(); it != rememberedTracks.end(); ++it)
  {
    std::vector<G4Track*> vector = it->second;
    for (auto it2 = vector.begin(); it2 != vector.end(); it2++){
      if ((std::find(trackToKill.begin(), trackToKill.end(), *it2) == trackToKill.end())){
        //Method set pour clear les doublons au lieu de find.
        trackToKill.push_back(*it2);
      }
    }
  }

  for (auto it = trackToKill.begin(); it != trackToKill.end(); ++it){
    delete *it;
  }

std::vector<G4Step*> stepToKill = {};
  for (auto it = rememberedSteps.begin(); it != rememberedSteps.end(); ++it)
  {
    std::vector<G4Step*> vector = it->second;
    for (auto it2 = vector.begin(); it2 != vector.end(); it2++){
      if ((std::find(stepToKill.begin(), stepToKill.end(), *it2) == stepToKill.end())){
        stepToKill.push_back(*it2);
      }
    }
  }

  for (auto it = stepToKill.begin(); it != stepToKill.end(); ++it){
    delete *it;
  }
}

void GateLastVertexInteractionSplittingActor::RememberLastProcessInformation(G4Step *step)
{

  // When an interesting process to split occurs, we remember the status of the track and the process at this current step
  // some informations regarding the track info have to be changed because they were update according to the interaction that occured
  // These informations are stocked as a map object, binding the track ID with all the track objects and processes to split.
  // Because in some cases, if a secondary was created before an interaction chain, this secondary will be track after the chain and
  // without this association, we wll loose the information about the process occuring for this secondary.

  G4String creatorProcessName = "None";
  if (step->GetTrack()->GetCreatorProcess() != 0)
    creatorProcessName = step->GetTrack()->GetCreatorProcess()->GetProcessName();
  G4String processName = "None";
  G4int trackID = step->GetTrack()->GetTrackID();
  G4int parentID = step->GetTrack()->GetParentID();
  //<<processName<<"    "<<step->GetTrack()->GetParticleDefinition()->GetParticleName()<<"    "<<step->GetTrack()->GetTrackStatus()<<std::endl;
  if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0)
  {
    processName = step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName();
  }
  if ((step->GetTrack()->GetParticleDefinition()->GetParticleName() == "e+") && ((step->GetTrack()->GetTrackStatus() == 1) || (step->GetTrack()->GetTrackStatus() == 2)))
  {
    processName = "annihil";
  }

  if ((std::find(fListOfProcesses.begin(), fListOfProcesses.end(), processName) != fListOfProcesses.end()))
  {
    G4Track *trackInformation = new G4Track(*(step->GetTrack()));
    G4Step *stepInformation = new G4Step(*(step));

    G4StepPoint *stepPoint = nullptr;
    stepPoint = step->GetPreStepPoint();

    
    trackInformation->SetKineticEnergy(stepPoint->GetKineticEnergy());
    if ((processName == "eBrem") || ((processName == "annihil")&& step->GetTrack()->GetTrackStatus() == 1)){
      trackInformation->SetKineticEnergy(stepPoint->GetKineticEnergy() - step->GetTotalEnergyDeposit());
    }
    trackInformation->SetMomentumDirection(stepPoint->GetMomentumDirection());
    if ((processName =="annihil") && ((step->GetTrack()->GetTrackStatus() == 1)))
      trackInformation->SetTrackStatus(fStopButAlive);
    else{
      trackInformation->SetTrackStatus(fAlive);
    }
    trackInformation->SetPolarization(stepPoint->GetPolarization());
    //trackInformation->SetPosition(stepPoint->GetPosition());

    if (auto search = fRememberedTracks.find(trackID); search != fRememberedTracks.end())
    {
      fRememberedTracks[trackID].push_back(trackInformation);
      fRememberedProcesses[trackID].push_back(processName);
      fRememberedSteps[trackID].push_back(stepInformation);
    }

    else
    {
      fRememberedTracks[trackID] = {trackInformation};
      fRememberedProcesses[trackID] = {processName};
      fRememberedSteps[trackID] = {stepInformation};
    }
  }

  else
  {
    if (auto search = fRememberedTracks.find(trackID); search == fRememberedTracks.end())
    {
      if (auto search = fRememberedTracks.find(parentID); search != fRememberedTracks.end())
      {
        if (auto it = std::find(fRememberedProcesses[parentID].begin(), fRememberedProcesses[parentID].end(), creatorProcessName); it != fRememberedProcesses[parentID].end())
        {
          auto idx = it - fRememberedProcesses[parentID].begin();
          fRememberedTracks[trackID] = {new G4Track(*fRememberedTracks[parentID][idx])};
          fRememberedProcesses[trackID] = {fRememberedProcesses[parentID][idx]};
          fRememberedSteps[trackID] = {new G4Step(*fRememberedSteps[parentID][idx])};
        }
        else
        {
          fRememberedTracks[trackID] = {new G4Track(*fRememberedTracks[parentID][0])};
          fRememberedProcesses[trackID] = {fRememberedProcesses[parentID][0]};
          fRememberedSteps[trackID] = {new G4Step(*fRememberedSteps[parentID][0])};
        }
      }
    }
  }
}

void GateLastVertexInteractionSplittingActor::CreateNewParticleAtTheLastVertex(G4Step *CurrentStep, G4Track* track, const G4Step *step, G4String processName)
{
  // We retrieve the process associated to the process name to split and we split according the process.
  // Since for compton scattering, the gamma is not a secondary particles, this one need to have his own splitting function.
  G4ParticleDefinition *particleDefinition = track->GetDefinition();
  G4ProcessManager *processManager = particleDefinition->GetProcessManager();
  G4ProcessVector *processList = processManager->GetProcessList();
  
  G4VProcess *processToSplit = nullptr;
  for (size_t i = 0; i < processList->size(); ++i)
  {
    auto process = (*processList)[i];
    if (process->GetProcessName() == processName)
    {
      processToSplit = process;
    }
  }
  if (processName == "compt")
  {
    
    ComptonSplitting(CurrentStep, track, step, processToSplit);
  }
  
  else
  {
    SecondariesSplitting(CurrentStep, track, step, processToSplit);
  }
  
}

void GateLastVertexInteractionSplittingActor::ResetProcessesForEnteringParticles(G4Step *step)
{

  // This function reset the processes and track registered to be split each time a particle enters into a volume.
  // Here a new particle incoming is either a particle entering into the volume ( first pre step is a boundary of a mother volume
  // or first step trigger the actor and the vertex is not either the mother volume or a the fdaughter volume) or an event generated within
  // the volume (the particle did not enter into the volume and its parentID = 0). An additionnal condition is set with the trackID to ensure
  // particles crossing twice the volume (after either a compton or pair prod) are not splitted.

  G4int trackID = step->GetTrack()->GetTrackID();
  if ((fEventIDOfInitialSplittedTrack != fEventID) || ((fEventIDOfInitialSplittedTrack == fEventID) && (trackID < fTrackIDOfInitialTrack)))
  {
    G4String logicalVolumeNamePreStep = "None";
    if (step->GetPreStepPoint()->GetPhysicalVolume() != 0)
    {
      logicalVolumeNamePreStep = step->GetPreStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
    }
    if (((step->GetPreStepPoint()->GetStepStatus() == 1) && (logicalVolumeNamePreStep == fMotherVolumeName)) ||
        ((step->GetTrack()->GetLogicalVolumeAtVertex()->GetName() != logicalVolumeNamePreStep) && (step->GetTrack()->GetLogicalVolumeAtVertex()->GetName() != fMotherVolumeName)))
    {
      fTrackIDOfInitialTrack = trackID;
      fEventIDOfInitialSplittedTrack = fEventID;
      fWeightOfEnteringParticle = step->GetTrack()->GetWeight();
      ClearRememberedTracksAndSteps(fRememberedTracks,fRememberedSteps);
      fRememberedProcesses.clear();
      fRememberedTracks.clear();
      fRememberedSteps.clear();
    }
    else if (step->GetTrack()->GetParentID() == 0)
    {
      fTrackIDOfInitialTrack = trackID;
      fEventIDOfInitialSplittedTrack = fEventID;
      fWeightOfEnteringParticle = step->GetTrack()->GetWeight();
      ClearRememberedTracksAndSteps(fRememberedTracks,fRememberedSteps);
      fRememberedProcesses.clear();
      fRememberedTracks.clear();
      fRememberedSteps.clear();
    }
  }
}

void GateLastVertexInteractionSplittingActor::PostponeFirstAnnihilationTrackIfInteraction(G4Step *step, G4String processName)
{
  // In case the first gamma issued from annihilation undergoes an interaction, in order to not bias the process
  // We keep in memory the particle post step state (with its secondaries) and kill the particle and its secondaries.
  // If the second photon from annihilation exiting the collimation system with an interaction or is absorbed within
  // the collimation, the particle is subsequently resimulated, starting from the interaction point.

  G4int trackID = step->GetTrack()->GetTrackID();
  if (std::find(fListOfProcesses.begin(), fListOfProcesses.end(), processName) != fListOfProcesses.end())
  {
    fSuspendForAnnihil = true;
    G4Track trackToPostpone = G4Track(*(step->GetTrack()));
    trackToPostpone.SetKineticEnergy(step->GetPostStepPoint()->GetKineticEnergy());
    trackToPostpone.SetMomentumDirection(step->GetPostStepPoint()->GetMomentumDirection());
    trackToPostpone.SetTrackStatus(step->GetTrack()->GetTrackStatus());
    trackToPostpone.SetPolarization(step->GetPostStepPoint()->GetPolarization());
    trackToPostpone.SetPosition(step->GetPostStepPoint()->GetPosition());
    trackToPostpone.SetTrackID(trackID);
    fTracksToPostpone.push_back(trackToPostpone);
    auto theTrack = fTracksToPostpone[0];

    auto secVec = step->GetfSecondary();
    for (int i = 0; i < secVec->size(); i++)
    {
      G4Track *sec = (*secVec)[i];
      G4Track copySec = G4Track((*sec));
      fTracksToPostpone.push_back(copySec);
    }

    fTracksToPostpone[0].SetTrackID(trackID);
    step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
  }
}

void GateLastVertexInteractionSplittingActor::RegenerationOfPostponedAnnihilationTrack(G4Step *step)
{

  // If the second photon from annihilation suceed to exit the collimation system with at least one interaction or was absorbed.
  // Resimulation of annihilation photons and its potential secondaries.

  G4TrackVector *currentSecondaries = step->GetfSecondary();
  for (int i = 0; i < fTracksToPostpone.size(); i++)
  {
    G4Track *trackToAdd = new G4Track(fTracksToPostpone[fTracksToPostpone.size() - 1 - i]);
    trackToAdd->SetParentID(step->GetTrack()->GetTrackID() - 1);

    currentSecondaries->insert(currentSecondaries->begin(), trackToAdd);
  }
  G4Track *firstPostponedTrack = (*currentSecondaries)[0];

  // Handle of case were the interaction killed the photon issued from annihilation, it will not be track at the following state
  // and the boolean plus the track vector need to be reset

  if (firstPostponedTrack->GetTrackStatus() == 2)
  {
    fSuspendForAnnihil = false;
    fTracksToPostpone.clear();
  }
}

void GateLastVertexInteractionSplittingActor::HandleTrackIDIfPostponedAnnihilation(G4Step *step)
{
  // The ID is to modify trackID and the processes and tracks sotcked for a specific trackID associated to
  // the postponed annihilation to respect the trackID order in GEANT4. Since in this case the second photon is tracked before the first one
  // his trackID +=1. For the postponed one, he is the first secondary particle of the second photon tracks, his trackID is therefore equal
  // to the second photon trackID +1 instead of the second photon  trackID -1.
  // The parentID of secondary particles are also modified because they are used in the rememberlastprocess function
  // At last the value associated to a specific trackID in the process and track map are modified according to the new trackID.

  if (fSuspendForAnnihil)
  {
    if (step->GetTrack()->GetTrackID() == fTracksToPostpone[0].GetTrackID() - 1)
    {
      fRememberedProcesses[step->GetTrack()->GetTrackID()] = fRememberedProcesses[step->GetTrack()->GetTrackID() + 1];
      fRememberedProcesses.erase(step->GetTrack()->GetTrackID() + 1);
      fRememberedSteps[step->GetTrack()->GetTrackID()] = fRememberedSteps[step->GetTrack()->GetTrackID() + 1];
      fRememberedSteps.erase(step->GetTrack()->GetTrackID() + 1);
      fRememberedTracks[step->GetTrack()->GetTrackID()] = fRememberedTracks[step->GetTrack()->GetTrackID() + 1];
      fRememberedTracks.erase(step->GetTrack()->GetTrackID() + 1);
      auto vecSec = step->GetSecondary();
      for (int i = 0; i < vecSec->size(); i++)
      {
        (*vecSec)[i]->SetParentID(step->GetTrack()->GetTrackID() + 1);
      }
      step->GetTrack()->SetTrackID(step->GetTrack()->GetTrackID() + 1);
    }
    if (step->GetTrack()->GetTrackID() == fTracksToPostpone[0].GetTrackID() + 1)
    {
      auto vecSec = step->GetSecondary();
      for (int i = 0; i < vecSec->size(); i++)
      {
        (*vecSec)[i]->SetParentID(step->GetTrack()->GetTrackID() - 2);
      }
      step->GetTrack()->SetTrackID(step->GetTrack()->GetTrackID() - 2);
    }
  }
}

void GateLastVertexInteractionSplittingActor::BeginOfRunAction(const G4Run *run)
{

  // The way to behave of the russian roulette is the following :
  // we provide a vector director and the theta angle acceptance, where theta =
  // 0 is a vector colinear to the vector director Then if the track generated
  // is on the acceptance angle, we add it to the primary track, and if it's not
  // the case, we launch the russian roulette

  if (fRotationVectorDirector)
  {
    G4VPhysicalVolume *physBiasingVolume =
        G4PhysicalVolumeStore::GetInstance()->GetVolume(fMotherVolumeName);
    auto rot = physBiasingVolume->GetObjectRotationValue();
    fVectorDirector = rot * fVectorDirector;
  }
}

void GateLastVertexInteractionSplittingActor::BeginOfEventAction(const G4Event *event)
{

  fParentID = -1;
  fEventID = event->GetEventID();
  fEventIDOfSplittedTrack = -1;
  fTrackIDOfSplittedTrack = -1;
  fNotSplitted == true;
}

void GateLastVertexInteractionSplittingActor::PreUserTrackingAction(const G4Track *track)
{
  fIsFirstStep = true;
}

void GateLastVertexInteractionSplittingActor::SteppingAction(G4Step *step)
{
  
  G4String particleName = step->GetTrack()->GetParticleDefinition()->GetParticleName();
  G4String creatorProcessName = "None";

  
  if (step->GetTrack()->GetCreatorProcess() != 0)
    creatorProcessName = step->GetTrack()->GetCreatorProcess()->GetProcessName();


  //std::cout<<particleName<<"     "<<fEventID<<"   "<<step->GetTotalEnergyDeposit()<<"   "<<step->GetPreStepPoint()->GetKineticEnergy()<<"     "<<step->GetPreStepPoint()->GetMomentumDirection()<<step->GetTrack()->GetTrackID()<<"     "<<step->GetTrack()->GetWeight()<<"    "<<step->GetTrack()->GetParentID()<<"    "<<fTrackIDOfSplittedTrack<<std::endl;;


  if (fIsFirstStep)
  {
    ResetProcessesForEnteringParticles(step);
  }

  G4int trackID = step->GetTrack()->GetTrackID();


  if ((step->GetTrack()->GetWeight() < fWeightOfEnteringParticle) && (fNotSplitted ==false)){
    
    G4String logicalVolumeNamePostStep = "None";
    if (step->GetPostStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();


    G4String processName = "None";
    if (step->GetPostStepPoint()->GetProcessDefinedStep() != 0)
      processName = step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName();


    if (particleName != "e+"){
      if (std::find(fListOfProcesses.begin(), fListOfProcesses.end(), processName) != fListOfProcesses.end()){
        step->GetTrack()->SetTrackStatus(fStopAndKill);
        step->GetfSecondary()->clear();
      }
    }
    
    
    if ((particleName == "e+") && ((step->GetTrack()->GetTrackStatus() == 1)||(step->GetTrack()->GetTrackStatus() == 2))){
      step->GetTrack()->SetTrackStatus(fStopAndKill);
      step->GetfSecondary()->clear();
    }

    

    if ((step->GetTrack()->GetTrackStatus() == 2) || (step->GetTrack()->GetTrackStatus() == 3)){

      /*
      delete fTrackToSplit;
      delete fStepToSplit;
      fTrackToSplit = new G4Track(*fRememberedTracks[fTrackIDOfSplittedTrack].back());
      fStepToSplit = new G4Step(*fRememberedSteps[fTrackIDOfSplittedTrack].back());
      */

      CreateNewParticleAtTheLastVertex(step, fTrackToSplit, fStepToSplit, fProcessToSplit);
    
    }


    if (((step->GetTrack()->GetTrackStatus() != 2) && (step->GetTrack()->GetTrackStatus() != 3)) && (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(), logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()))
    {

      if (fSplitCounter < fWeightOfEnteringParticle) {
        /*
        delete fTrackToSplit;
        delete fStepToSplit;
        fTrackToSplit = new G4Track(*fRememberedTracks[fTrackIDOfSplittedTrack].back());
        fStepToSplit = new G4Step(*fRememberedSteps[fTrackIDOfSplittedTrack].back());
        */
        CreateNewParticleAtTheLastVertex(step, fTrackToSplit, fStepToSplit, fProcessToSplit);
        //std::cout<<fTrackToSplit<<"   "<<fStepToSplit<<std::endl;
        G4TrackVector *trackVector = step->GetfSecondary();
        G4Track* theTrack= trackVector->back();
        fSplitCounter += theTrack->GetWeight();
        //std::cout<<theTrack->GetWeight()<<std::endl;
        if (fSplitCounter >= fWeightOfEnteringParticle) {
          delete fTrackToSplit;
          delete fStepToSplit;
          fTrackToSplit = nullptr;
          fStepToSplit = nullptr;
          fSplitCounter = 0;
          fNotSplitted = true;
          fProcessToSplit = "None";
          theTrack->SetTrackStatus(fStopAndKill);
        }
      }
    }
    

  }

  
  if (step->GetTrack()->GetWeight() == fWeightOfEnteringParticle)
  {
    //std::cout<<particleName<<"    "<<step->GetTrack()->GetTrackStatus()<<std::endl;
    RememberLastProcessInformation(step);
    //std::cout<<particleName<<"    "<<step->GetTrack()->GetTrackStatus()<<std::endl;
    G4String process = "None";
    if (auto search = fRememberedProcesses.find(trackID); search != fRememberedProcesses.end())
    {
      process = fRememberedProcesses[trackID].back();
    }
    // std::cout<<step->GetTrack()->GetVertexPosition()<<"    "<<step->GetTrack()->GetParticleDefinition()->GetParticleName()<<"     "<<fSuspendForAnnihil<<"    "<<process<<"    "<<step->GetTrack()->GetWeight()<<"    "<<step->GetTrack()->GetParentID()<<"      "<<step->GetTrack()->GetTrackID()<<"    "<<creatorProcessName<<"       "<<step->GetTrack()->GetTrackStatus()<<"      "<<step->GetPreStepPoint()->GetKineticEnergy()<<"    " <<step->GetPostStepPoint()->GetKineticEnergy()<<"    "<<step->GetPreStepPoint()->GetPosition()<<"   "<<step->GetPostStepPoint()->GetPosition()<<std::endl;

    /*
    if ((!fSuspendForAnnihil) && (creatorProcessName == "annihil") && (fTrackIDOfSplittedTrack == step->GetTrack()->GetParentID()) && (fEventID == fEventIDOfSplittedTrack))
    {
      step->GetTrack()->SetTrackStatus(fKillTrackAndSecondaries);
    }
    */

    

    if ((particleName == "e-") && (step->GetTrack()->GetWeight() == fWeightOfEnteringParticle) && (creatorProcessName == "conv") && (fTrackIDOfSplittedTrack == step->GetTrack()->GetParentID()) && (fEventID == fEventIDOfSplittedTrack)){
      step->GetTrack()->SetTrackStatus(fStopAndKill);
    }


    /*
    if ((!fSuspendForAnnihil) && (process != "annihil") && (creatorProcessName == "annihil") && (step->GetTrack()->GetTrackStatus() != 3))
    {
      G4int parentID = step->GetTrack()->GetParentID();
      if (auto search = fRememberedProcesses.find(parentID); search != fRememberedProcesses.end())
      {
        if (fRememberedProcesses[trackID].back() == "annihil")
          PostponeFirstAnnihilationTrackIfInteraction(step, process);
      }
    }

    // If the first annihilation photon exit the collimation and the process to split is annihilation
    // We kill the second photon, because the annihilation will generate both the photons.

    if (fSuspendForAnnihil)
    {
      if (trackID == fTracksToPostpone[0].GetTrackID() - 1)
      {
        fSuspendForAnnihil = false;
        fTracksToPostpone.clear();
      }
    }
  */

    G4String logicalVolumeNamePostStep = "None";
    if (step->GetPostStepPoint()->GetPhysicalVolume() != 0)
      logicalVolumeNamePostStep = step->GetPostStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();

    if (((step->GetTrack()->GetTrackStatus() != 2) && (step->GetTrack()->GetTrackStatus() != 3)) && (std::find(fListOfVolumeAncestor.begin(), fListOfVolumeAncestor.end(), logicalVolumeNamePostStep) != fListOfVolumeAncestor.end()))
    {

      if (auto search = fRememberedProcesses.find(trackID); search != fRememberedProcesses.end()){
        
        fProcessToSplit = fRememberedProcesses[trackID].back();
        fTrackToSplit = new G4Track(*fRememberedTracks[trackID].back());
        fStepToSplit =  new G4Step(*fRememberedSteps[trackID].back());
        
      }
        

      if (std::find(fListOfProcesses.begin(), fListOfProcesses.end(), fProcessToSplit) != fListOfProcesses.end())
      {

        fTrackIDOfSplittedTrack = trackID;
        fEventIDOfSplittedTrack = fEventID;
        fTrackIDOfInitialSplittedTrack = fTrackIDOfInitialTrack;

        // Handle of pecularities (1):

        // If the process t split is the gamma issued from compton interaction, the electron primary generated have to be killed
        // given that electron will be regenerated

        if ((fProcessToSplit == "compt") && (particleName == "gamma"))
        {
          auto secondaries = step->GetfSecondary();
          if (secondaries->size() > 0)
          {
            G4Track *lastSecTrack = secondaries->back();
            lastSecTrack->SetTrackStatus(fStopAndKill);
          }
        }

        

        // Handle of pecularities (2):

        // If the process to split is the annihilation, the second photon, postponed or not, have to be killed
        // the reset of the postpone is performed here, whereas the kill of the next annihilation photon, if not postponed
        // is realised at the beginning of the step tracking.
        /*
        if (fProcessToSplit == "annihil")
        {
          if (fSuspendForAnnihil)
          {
            fSuspendForAnnihil = false;
            fTracksToPostpone.clear();
          }
        }
        */
         // Handle of pecularities 3 :  If the positron which created one or more brem photons exits
         // all the brems photons will be killed before their tracking, and the conv processes will then be replayed

        if ((particleName == "e+") &&(fProcessToSplit != "None")) {

          G4int parentID = step->GetTrack()->GetParentID();
          fProcessToSplit = fRememberedProcesses[parentID].back();
          delete fTrackToSplit;
          delete fStepToSplit;
          fTrackToSplit = new G4Track(*fRememberedTracks[parentID].back());
          fStepToSplit = new G4Step(*fRememberedSteps[parentID].back());
          fTrackIDOfInitialTrack = parentID;

          auto* vecSecondaries = step->GetfSecondary();
          vecSecondaries->clear();

        }
          if (!((fProcessToSplit == "eBrem") && (particleName == "e-")))
          {
          CreateNewParticleAtTheLastVertex(step, fTrackToSplit, fStepToSplit, fProcessToSplit);
          fNotSplitted = false;
          }
          step->GetTrack()->SetTrackStatus(fStopAndKill);


        
        
        
      }
    }
  }

  /*
  if ((fSuspendForAnnihil) && ((step->GetTrack()->GetTrackStatus() == 1) || (step->GetTrack()->GetTrackStatus() == 2)))
  {
    if (trackID == fTracksToPostpone[0].GetTrackID())
    {
      RegenerationOfPostponedAnnihilationTrack(step);
    }
  }
  */

  fIsFirstStep = false;
  
}



void GateLastVertexInteractionSplittingActor::PostUserTrackingAction(const G4Track *track)
{
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
