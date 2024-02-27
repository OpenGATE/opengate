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
/// \file GateOptnComptSplittingForTransportation.cc
/// \brief Implementation of the GateOptnComptSplittingForTransportation class

#include "GateOptnComptSplittingForTransportation.h"
#include "G4BiasingProcessInterface.hh"

#include "G4ComptonScattering.hh"
#include "G4DynamicParticle.hh"
#include "G4Exception.hh"
#include "G4Gamma.hh"
#include "G4GammaConversion.hh"
#include "G4ParticleChange.hh"
#include "G4ParticleChangeForGamma.hh"
#include "G4PhotoElectricEffect.hh"
#include "G4ProcessType.hh"
#include "G4RayleighScattering.hh"
#include "G4SystemOfUnits.hh"
#include "G4TrackStatus.hh"
#include "G4TrackingManager.hh"
#include "G4VEmProcess.hh"
#include <memory>

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptnComptSplittingForTransportation::
    GateOptnComptSplittingForTransportation(G4String name)
    : G4VBiasingOperation(name), fSplittingFactor(1),
      fRussianRouletteForAngle(false), fParticleChange() {}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptnComptSplittingForTransportation::
    ~GateOptnComptSplittingForTransportation() {}

G4VParticleChange *
GateOptnComptSplittingForTransportation::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {

  // Here we generate for the first the  compton process, given that this
  // function (ApplyFinalStateBiasing) is called when there is a compton
  // interaction Then the interaction location of the compton process will
  // always be the same

  G4double globalTime = step->GetTrack()->GetGlobalTime();
  const G4ThreeVector position = step->GetPostStepPoint()->GetPosition();
  G4int nCalls = 1;
  G4int splittingFactor = ceil(fSplittingFactor);
  G4double survivalProbabilitySplitting =
      1 - (splittingFactor - fSplittingFactor) / splittingFactor;
  G4bool isRightAngle = false;
  G4double gammaWeight = 0;
  G4int nbSecondaries = 0;
  G4VParticleChange *processFinalState = nullptr;
  G4ParticleChangeForGamma *castedProcessInitFinalState = nullptr;

  processFinalState =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
  // In case we don't want to split (a bit faster) i.e no biaising or no
  // splitting low weights particles.

  if (fSplittingFactor == 1 && fRussianRouletteForAngle == false)
    return processFinalState;

  castedProcessInitFinalState = (G4ParticleChangeForGamma *)processFinalState;
  nbSecondaries = processFinalState->GetNumberOfSecondaries();

  fParticleChange.Initialize(*track);
  fParticleChange.ProposeWeight(track->GetWeight());
  fParticleChange.ProposeTrackStatus(
      castedProcessInitFinalState->GetTrackStatus());
  fParticleChange.ProposeEnergy(
      castedProcessInitFinalState->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      castedProcessInitFinalState->GetProposedMomentumDirection());
  fParticleChange.SetSecondaryWeightByProcess(true);

  // If there is cut on secondary particles, there is a probability that the
  // electron is not simulated Then, if the compton process created it, we add
  // the gien electron to the ParticleChange object
  if (nbSecondaries == 1) {
    G4Track *initElectronTrack = castedProcessInitFinalState->GetSecondary(0);
    initElectronTrack->SetWeight(track->GetWeight());
    fParticleChange.AddSecondary(initElectronTrack);
  }

  processFinalState->Clear();
  castedProcessInitFinalState->Clear();

  // There is here the biasing process :
  //  Since G4VParticleChange class does not allow to retrieve scattered gamma
  //  information, we need to cast the type G4ParticleChangeForGamma to the
  //  G4VParticleChange object. We then call the process (biasWrapper(compt))
  //  fSplittingFactor times (Here, the difference with the other version of
  //  splitting is the primary particle will be killed and its weight does not
  //  count)  to generate, at last, fSplittingFactor gamma according to the
  //  compton interaction process. If the gamma track is ok regarding the
  //  russian roulette algorithm (no russian roulette
  //, or within the acceptance angle, or not killed by the RR process), we add
  // it to the primary track.
  //  If an electron is generated (above the range cut), we also generate it.
  //  A tremendous advantage is there is no need to use by ourself Klein-Nishina
  //  formula or other. So, if the physics list used takes into account the
  //  doppler broadening or other fine effects, this will be also taken into
  //  account by the MC simulation. PS : The first gamma is then the primary
  //  particle, but all the other splitted particle (electron of course AND
  //  gamma) must be considered as secondary particles, even though generated
  //  gamma will not be cut here by the applied cut.

  G4int simulationTrackID = 0;
  while (nCalls <= splittingFactor) {
    gammaWeight = track->GetWeight() / fSplittingFactor;
    G4double initGammaWeight = track->GetWeight();
    G4VParticleChange *processGammaSplittedFinalState =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    G4ParticleChangeForGamma *castedProcessGammaSplittedFinalState =
        (G4ParticleChangeForGamma *)processGammaSplittedFinalState;
    const G4ThreeVector momentum =
        castedProcessGammaSplittedFinalState->GetProposedMomentumDirection();
    G4double energy =
        castedProcessGammaSplittedFinalState->GetProposedKineticEnergy();
    G4double cosTheta =
        fVectorDirector *
        castedProcessInitFinalState->GetProposedMomentumDirection();
    G4double theta = std::acos(cosTheta);
    G4double splittingProbability = G4UniformRand();

    if (splittingProbability <= survivalProbabilitySplitting ||
        survivalProbabilitySplitting == 1) {
      if ((fRussianRouletteForAngle == true) && (theta > fMaxTheta)) {
        G4double probability = G4UniformRand();
        if (probability < 1 / fSplittingFactor) {
          // Specific case where the russian roulette probability is
          // 1/splitting. Each particle generated, with a 1/split probability
          // will have a 1/split probability to survive with a final weight of
          // Initial weights * 1/split * split = Initial weight
          gammaWeight = gammaWeight * fSplittingFactor;
          G4Track *gammaTrack = new G4Track(*track);
          gammaTrack->SetWeight(gammaWeight);
          gammaTrack->SetKineticEnergy(energy);
          gammaTrack->SetMomentumDirection(momentum);
          gammaTrack->SetPosition(position);
          fParticleChange.AddSecondary(gammaTrack);
          simulationTrackID++;
          if (processGammaSplittedFinalState->GetNumberOfSecondaries() == 1) {
            G4Track *electronTrack =
                processGammaSplittedFinalState->GetSecondary(0);
            electronTrack->SetWeight(gammaWeight);
            fParticleChange.AddSecondary(electronTrack);
            simulationTrackID++;
          }
        }
      }

      if ((fRussianRouletteForAngle == false) ||
          ((fRussianRouletteForAngle == true) && (theta <= fMaxTheta))) {
        G4Track *gammaTrack = new G4Track(*track);
        gammaTrack->SetWeight(gammaWeight);
        gammaTrack->SetKineticEnergy(energy);
        gammaTrack->SetMomentumDirection(momentum);
        gammaTrack->SetPosition(position);
        fParticleChange.AddSecondary(gammaTrack);
        simulationTrackID++;
        if (processGammaSplittedFinalState->GetNumberOfSecondaries() == 1) {
          G4Track *electronTrack =
              processGammaSplittedFinalState->GetSecondary(0);
          electronTrack->SetWeight(gammaWeight);
          fParticleChange.AddSecondary(electronTrack);
          simulationTrackID++;
        }
      }
    }
    nCalls++;
    processGammaSplittedFinalState->Clear();
    castedProcessGammaSplittedFinalState->Clear();
  }
  return &fParticleChange;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
