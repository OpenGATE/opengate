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
/// \file GateOptnVGenericSplitting.cc
/// \brief Implementation of the GateOptnVGenericSplitting class

#include "GateOptnVGenericSplitting.h"
#include "G4BiasingProcessInterface.hh"

#include "G4ComptonScattering.hh"
#include "G4DynamicParticle.hh"
#include "G4Exception.hh"
#include "G4Gamma.hh"
#include "G4GammaConversion.hh"
#include "G4ParticleChange.hh"
#include "G4ParticleChangeForGamma.hh"
#include "G4ParticleChangeForLoss.hh"
#include "G4PhotoElectricEffect.hh"
#include "G4ProcessType.hh"
#include "G4RayleighScattering.hh"
#include "G4SystemOfUnits.hh"
#include "G4TrackStatus.hh"
#include "G4TrackingManager.hh"
#include "G4VEmProcess.hh"
#include <memory>

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptnVGenericSplitting::
    GateOptnVGenericSplitting(G4String name)
    : G4VBiasingOperation(name), fParticleChange() {}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptnVGenericSplitting::
    ~GateOptnVGenericSplitting() {}


void GateOptnVGenericSplitting::TrackInitializationChargedParticle(G4ParticleChange* particleChange,G4VParticleChange* processFinalState, const G4Track* track,G4double split) {

  G4ParticleChangeForLoss* processFinalStateForLoss =( G4ParticleChangeForLoss* ) processFinalState ;
  particleChange->Initialize(*track);
  particleChange->ProposeTrackStatus(processFinalStateForLoss->GetTrackStatus() );
  particleChange->ProposeEnergy(processFinalStateForLoss->GetProposedKineticEnergy() );
  particleChange->ProposeMomentumDirection(processFinalStateForLoss->GetProposedMomentumDirection());
  particleChange->SetNumberOfSecondaries(fSplittingFactor);
  particleChange->SetSecondaryWeightByProcess(true);
  processFinalStateForLoss->Clear();
}

void GateOptnVGenericSplitting::TrackInitializationGamma(G4ParticleChange* particleChange,G4VParticleChange* processFinalState, const G4Track* track,G4double split) {
  G4ParticleChangeForGamma* processFinalStateForGamma = (G4ParticleChangeForGamma *)processFinalState;
  particleChange->Initialize(*track);
  particleChange->ProposeTrackStatus(processFinalStateForGamma->GetTrackStatus() );
  particleChange->ProposeEnergy(processFinalStateForGamma->GetProposedKineticEnergy() );
  particleChange->ProposeMomentumDirection(processFinalStateForGamma->GetProposedMomentumDirection() );
  particleChange->SetNumberOfSecondaries(fSplittingFactor);
  particleChange->SetSecondaryWeightByProcess(true);
  processFinalStateForGamma->Clear();


}

G4double GateOptnVGenericSplitting::RussianRouletteForAngleSurvival(G4ThreeVector dir,G4ThreeVector vectorDirector,G4double maxTheta,G4double split){
G4double cosTheta =vectorDirector * dir;
G4double theta = std::acos(cosTheta);
G4double weightToApply = 1;
if (theta > maxTheta){
  G4double probability = G4UniformRand();
  if (probability <= 1 / split) {
    weightToApply = split;
  }
  else{
    weightToApply = 0;
  }
}
return weightToApply;
            
}


//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
