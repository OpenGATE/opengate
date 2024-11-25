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
#ifndef SimpleContainer_h
#define SimpleContainer_h

#include "G4Electron.hh"
#include "G4EmBiasingManager.hh"
#include "G4EmParameters.hh"
#include "G4EntanglementAuxInfo.hh"
#include "G4Gamma.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4PhysicalConstants.hh"
#include "G4PhysicsModelCatalog.hh"
#include "G4Positron.hh"
#include "G4Track.hh"
#include "G4VEmProcess.hh"
#include "G4VEnergyLossProcess.hh"
#include "G4VParticleChange.hh"
#include "G4eeToTwoGammaModel.hh"
#include "G4eplusAnnihilation.hh"
#include "G4eplusAnnihilationEntanglementClipBoard.hh"
#include <iostream>

class SimpleContainer {

public:
  SimpleContainer(G4String processName, G4double energy, G4ThreeVector momentum,
                  G4ThreeVector position, G4ThreeVector polarization,
                  G4String name, G4double weight, G4int trackStatus,
                  G4int nbSec, G4String flag, G4double length,
                  G4ThreeVector prePos) {

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

  SimpleContainer() {}

  ~SimpleContainer() {}

  void SetProcessNameToSplit(G4String processName) {
    fProcessNameToSplit = processName;
  }

  G4String GetProcessNameToSplit() { return fProcessNameToSplit; }

  void SetEnergy(G4double energy) { fEnergyToSplit = energy; }

  G4double GetEnergy() { return fEnergyToSplit; }

  void SetWeight(G4double weight) { fWeightToSplit = weight; }

  G4double GetWeight() { return fWeightToSplit; }

  void SetPolarization(G4ThreeVector polarization) {
    fPolarizationToSplit = polarization;
  }

  G4ThreeVector GetPolarization() { return fPolarizationToSplit; }

  void SetMomentum(G4ThreeVector momentum) { fMomentumToSplit = momentum; }

  G4ThreeVector GetMomentum() { return fMomentumToSplit; }

  void SetVertexPosition(G4ThreeVector position) {
    fPositionToSplit = position;
  }

  G4ThreeVector GetVertexPosition() { return fPositionToSplit; }

  void SetParticleNameToSplit(G4String name) { fParticleNameToSplit = name; }

  G4String GetParticleNameToSplit() { return fParticleNameToSplit; }

  void SetTrackStatus(G4int trackStatus) { fTrackStatusToSplit = trackStatus; }

  G4int GetTrackStatus() { return fTrackStatusToSplit; }

  void SetNbOfSecondaries(G4int nbSec) { fNumberOfSecondariesToSplit = nbSec; }

  G4int GetNbOfSecondaries() { return fNumberOfSecondariesToSplit; }

  void SetAnnihilationFlag(G4String flag) { fAnnihilProcessFlag = flag; }

  G4String GetAnnihilationFlag() { return fAnnihilProcessFlag; }

  void SetStepLength(G4double length) { fStepLength = length; }

  G4double GetStepLength() { return fStepLength; }

  void SetPrePositionToSplit(G4ThreeVector prePos) { fPrePosition = prePos; }

  G4ThreeVector GetPrePositionToSplit() { return fPrePosition; }

  void DumpInfoToSplit() {
    std::cout << "Particle name of the particle to split: "
              << fParticleNameToSplit << std::endl;
    std::cout << "Kinetic Energy of the particle to split: " << fEnergyToSplit
              << std::endl;
    std::cout << "Momentum of the particle to split: " << fMomentumToSplit
              << std::endl;
    std::cout << "Initial position of the particle to split: "
              << fPositionToSplit << std::endl;
    std::cout << "ProcessNameToSplit: " << fProcessNameToSplit << std::endl;
    std::cout << " " << std::endl;
  }

private:
  G4String fParticleNameToSplit = "None";
  G4String fProcessNameToSplit = "None";
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
};

#endif
