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
///
#ifndef LastVertexDataContainer_h
#define LastVertexDataContainer_h


#include <iostream>
#include "G4VEnergyLossProcess.hh"
#include "G4Track.hh"
#include "G4VEmProcess.hh"
#include "G4VParticleChange.hh"
#include "G4eplusAnnihilation.hh"
#include "G4PhysicalConstants.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4Gamma.hh"
#include "G4Electron.hh"
#include "G4Positron.hh"
#include "G4eeToTwoGammaModel.hh"
#include "G4EmBiasingManager.hh"
#include "G4EntanglementAuxInfo.hh"
#include "G4eplusAnnihilationEntanglementClipBoard.hh"
#include "G4EmParameters.hh"
#include "G4PhysicsModelCatalog.hh"


class LastVertexDataContainer{

public :

LastVertexDataContainer(G4ThreeVector interactionPosition, G4ThreeVector momentum,G4ThreeVector polarization, G4double energy,G4int trackID,G4String creationProcessName){

  fPositionToSplit= interactionPosition;
  fMomentumToSplit = momentum;
  fEnergyToSplit = energy;
  fIsExit = false;
  fToRegenerate = false;
  fTrackID = trackID;
  fCreationProcessName = creationProcessName;
  fPolarizationToSplit = polarization;
  
}


LastVertexDataContainer(){}

~LastVertexDataContainer(){}

void SetProcessNameToSplit(G4String processName){
  fProcessNameToSplit = processName;
}

G4String GetProcessNameToSplit(){
  return fProcessNameToSplit;
}

void SetEnergy(G4double energy){
  fEnergyToSplit =energy;
}

G4double GetEnergy(){
  return fEnergyToSplit;
}


void SetWeight(G4double weight){
  fWeightToSplit =weight;
}

G4double GetWeight(){
  return fWeightToSplit;
}

void SetPolarization(G4ThreeVector polarization){
  fPolarizationToSplit = polarization;
}

G4ThreeVector GetPolarization(){
  return fPolarizationToSplit;
}

void SetMomentum(G4ThreeVector momentum){
  fMomentumToSplit =momentum;
}

G4ThreeVector GetMomentum(){
  return fMomentumToSplit;
}

void SetVertexPosition(G4ThreeVector position){
  fPositionToSplit = position;
}

G4ThreeVector GetVertexPosition(){
  return fPositionToSplit;
}

void SetExitingStatus(G4bool isExit){
  fIsExit = isExit;
}

G4bool GetExitingStatus(){
  return fIsExit;
}


void SetRegenerationStatus(G4bool toRegenerate){
  fToRegenerate= toRegenerate;
}

G4bool GetRegenerationStatus(){
  return fToRegenerate;
}



void SetTrackID(G4int trackID ){
  fTrackID = trackID;
}

G4int GetTrackID(){
  return fTrackID;
}


void SetParticleName(G4String name){
  fParticleName = name;
}

G4String GetParticleName(){
  return fParticleName;
}

void SetParticleNameToSplit(G4String name){
  fParticleNameToSplit = name;
}

G4String GetParticleNameToSplit(){
  return fParticleNameToSplit;
}


void SetCreationProcessName(G4String creationProcessName){
  fCreationProcessName = creationProcessName;
}

G4String GetCreationProcessName(){
  return fCreationProcessName;
}



void SetTrackStatus(G4int trackStatus){
  fTrackStatusToSplit = trackStatus;
}


G4int GetTrackStatus(){
  return fTrackStatusToSplit;
}


void SetNbOfSecondaries(G4int nbSec){
  fNumberOfSecondariesToSplit = nbSec;
}

G4int GetNbOfSecondaries(){
  return fNumberOfSecondariesToSplit;
}

void SetAnnihilationFlag(G4String flag){
  fAnnihilProcessFlag = flag;
}

G4String GetAnnihilationFlag(){
  return fAnnihilProcessFlag;
}

void SetStepLength(G4double length){
  fStepLength = length;
}

G4double GetStepLength(){
  return fStepLength;
}



void SetSplittingParameters(G4String processName,G4double energy,G4ThreeVector momentum, G4ThreeVector position,G4ThreeVector polarization,G4String name,G4double weight,G4int trackStatus,G4int nbSec,G4String flag,G4double length, G4ThreeVector prePos){
  fProcessNameToSplit = processName;
  fEnergyToSplit = energy;
  fMomentumToSplit = momentum;
  fPositionToSplit = position;
  fPolarizationToSplit = polarization;
  fParticleNameToSplit = name;
  fWeightToSplit = weight;
  fTrackStatusToSplit = trackStatus;
  fNumberOfSecondariesToSplit = nbSec;
  fAnnihilProcessFlag = flag;
  fStepLength = length;
  fPrePosition = prePos;
}





void PushListOfSplittingParameters(G4String processName,G4double energy,G4ThreeVector momentum, G4ThreeVector position,G4ThreeVector polarization,G4String name,G4double weight, G4int trackStatus,G4int nbSec, G4String flag,G4double length,G4ThreeVector prePos){
  fVectorOfProcessToSplit.push_back(processName);
  fVectorOfEnergyToSplit.push_back(energy);
  fVectorOfMomentumToSplit.push_back(momentum);
  fVectorOfPositionToSplit.push_back(position);
  fVectorOfPolarizationToSplit.push_back(polarization);
  fVectorOfParticleNameToSplit.push_back(name);
  fVectorOfWeightToSplit.push_back(weight);
  fVectorOfTrackStatusToSplit.push_back(trackStatus);
  fVectorOfNumberOfSecondariesToSplit.push_back(nbSec);
  fVectorOfAnnihilProcessFlag.push_back(flag);
  fVectorOfStepLength.push_back(length);
  fVectorOfPrePosition.push_back(prePos);
  
}


LastVertexDataContainer ContainerFromParentInformation(G4Step* step){
  LastVertexDataContainer aContainer = LastVertexDataContainer();
  aContainer.fTrackID = step->GetTrack()->GetTrackID();
  aContainer.fParticleName = step->GetTrack()->GetDefinition()->GetParticleName();
  if (this->fProcessNameToSplit != "None"){
    if (this->fVectorOfProcessToSplit.size() !=0){
      G4ThreeVector vertexPosition = step->GetTrack()->GetVertexPosition();
      for (int i =0;i<this->fVectorOfPositionToSplit.size();i++){
        if (vertexPosition == this->fVectorOfPositionToSplit[i]){
          aContainer.SetSplittingParameters(this->fVectorOfProcessToSplit[i],this->fVectorOfEnergyToSplit[i],this->fVectorOfMomentumToSplit[i],this->fVectorOfPositionToSplit[i],this->fVectorOfPolarizationToSplit[i],this->fVectorOfParticleNameToSplit[i],this->fVectorOfWeightToSplit[i], this->fVectorOfTrackStatusToSplit[i], this->fVectorOfNumberOfSecondariesToSplit[i], this->fVectorOfAnnihilProcessFlag[i],this->fVectorOfStepLength[i],this->fVectorOfPrePosition[i]);
          return aContainer;
        }
      }
    }
    else{
      aContainer.SetSplittingParameters(this->fProcessNameToSplit,this->fEnergyToSplit,this->fMomentumToSplit,this->fPositionToSplit,this->fPolarizationToSplit,this->fParticleNameToSplit,this->fWeightToSplit, this->fTrackStatusToSplit, this->fNumberOfSecondariesToSplit, this->fAnnihilProcessFlag,this->fStepLength,this->fPrePosition);
      return aContainer;
    }
  }
  return aContainer;
}







void DumpInfoToSplit(){
  std::cout<<"Particle name of the particle to split: "<<fParticleNameToSplit<<std::endl;
  std::cout<<"Kinetic Energy of the particle to split: "<<fEnergyToSplit<<std::endl;
  std::cout<<"Momentum of the particle to split: "<<fMomentumToSplit<<std::endl;
  std::cout<<"Initial position of the particle to split: "<<fPositionToSplit<<std::endl;
  std::cout<<"ProcessNameToSplit: "<<fProcessNameToSplit<<std::endl;
  std::cout<<"trackID of current particle: "<<fTrackID<<std::endl;
  std::cout<<"Exiting status of current particle: "<<fIsExit<<std::endl;
  std::cout<<"Regeneration status of current particle: "<<fToRegenerate<<std::endl;
  std::cout<<"ParticleName of current particle: "<<fParticleName<<std::endl;
  std::cout<<" "<<std::endl;

}


friend std::ostream& operator<<(std::ostream& os, const LastVertexDataContainer& container) {
    os <<container.fParticleName<<" ID: "<<container.fTrackID<< "process: "<< container.fCreationProcessName;
    return os;
}




private :

G4String fParticleName="None";
G4String fParticleNameToSplit="None";
G4bool fIsExit =false;
G4bool fToRegenerate = false;
G4int fTrackID = 0;
G4String fCreationProcessName ="None";
G4String fProcessNameToSplit ="None";
G4double fEnergyToSplit = 0;
G4ThreeVector fMomentumToSplit;
G4ThreeVector fPositionToSplit;
G4ThreeVector fPolarizationToSplit;
G4double fWeightToSplit;
G4int fTrackStatusToSplit;
G4int fNumberOfSecondariesToSplit;
G4String fAnnihilProcessFlag;
G4double fStepLength;
G4ThreeVector fPrePosition;

std::vector<G4ThreeVector> fVectorOfMomentumToSplit;
std::vector<G4ThreeVector> fVectorOfPositionToSplit;
std::vector<G4ThreeVector> fVectorOfPolarizationToSplit;
std::vector<G4double> fVectorOfEnergyToSplit;
std::vector<G4String> fVectorOfProcessToSplit;
std::vector<G4String> fVectorOfParticleNameToSplit;
std::vector<G4double> fVectorOfWeightToSplit;
std::vector<G4int>fVectorOfTrackStatusToSplit;
std::vector<G4int>fVectorOfNumberOfSecondariesToSplit;
std::vector<G4String>fVectorOfAnnihilProcessFlag;
std::vector<G4double>fVectorOfStepLength;
std::vector<G4ThreeVector>fVectorOfPrePosition;




};

#endif





  