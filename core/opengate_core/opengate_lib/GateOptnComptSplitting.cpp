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
/// \file GateOptnComptSplitting.cc
/// \brief Implementation of the GateOptnComptSplitting class

#include "GateOptnComptSplitting.h"
#include "G4BiasingProcessInterface.hh"

#include "G4DynamicParticle.hh"
#include "G4Exception.hh"
#include "G4Gamma.hh"
#include "G4ParticleChange.hh"
#include "G4ParticleChangeForGamma.hh"
#include "G4SystemOfUnits.hh"
#include "G4TrackStatus.hh"
#include <memory>

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptnComptSplitting::GateOptnComptSplitting(G4String name)
    : G4VBiasingOperation(name), fSplittingFactor(1), fRussianRoulette(false),
      fParticleChange() {}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

GateOptnComptSplitting::~GateOptnComptSplitting() {}

G4VParticleChange *GateOptnComptSplitting::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {

  // Here we generate for the first the "fake" compton process, given that this
  // function (ApplyFinalStateBiasing) is called when there is a compton
  // interaction Then the interaction location of the compton process will
  // always be the same

  // Initialisation of parameter for the split, because the photon is the
  // primary particle, so it's a bit tricky

  G4double globalTime = step->GetTrack()->GetGlobalTime();
  const G4ThreeVector position = step->GetPostStepPoint()->GetPosition();
  G4int nCalls = 0;
  G4int splittingFactor = ceil(fSplittingFactor);
  G4double survivalProbabilitySplitting =
      1 - (splittingFactor - fSplittingFactor) / splittingFactor;
  G4bool isRightAngle = false;
  G4double gammaWeight = 0;
  G4int nbSecondaries = 0;
  G4VParticleChange *processFinalState = nullptr;
  G4ParticleChangeForGamma *castedProcessInitFinalState = nullptr;

  while (isRightAngle == false) {
    gammaWeight = track->GetWeight() / fSplittingFactor;
    processFinalState =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    // In case we don't want to split (a bit faster) i.e no biaising or no
    // splitting low weights particles.

    if ((fSplittingFactor == 1 && fRussianRoulette == false) ||
        track->GetWeight() < fWeightThreshold)
      return processFinalState;

    castedProcessInitFinalState = (G4ParticleChangeForGamma *)processFinalState;
    nbSecondaries = processFinalState->GetNumberOfSecondaries();
    G4ThreeVector initMomentum =
        castedProcessInitFinalState->GetProposedMomentumDirection();
    G4double cosTheta = fVectorDirector * initMomentum;
    G4double theta = std::acos(cosTheta);

    G4double splittingProbability = G4UniformRand();
    if (splittingProbability <= survivalProbabilitySplitting ||
        survivalProbabilitySplitting == 1) {

      // If the number of compton interaction is too high, we simply return the
      // process, instead of generating very low weight particles.
      if (track->GetWeight() <= fMinWeightOfParticle) {
        return processFinalState;
      }

      // If the russian roulette is activated, we need to initialize the track
      // with a primary particle which have the right angle That's why nCall is
      // also incremented here, to avoid any bias in te number of gamma
      // generated
      if ((fRussianRoulette == true) && (theta > fMaxTheta)) {
        G4double probability = G4UniformRand();
        if (probability < 1 / fSplittingFactor) {
          gammaWeight = gammaWeight * fSplittingFactor;
          isRightAngle = true;
        }
      }

      if ((fRussianRoulette == false) ||
          ((fRussianRoulette == true) && (theta <= fMaxTheta)))
        isRightAngle = true;
    }

    if (isRightAngle == false)
      processFinalState->Clear();

    // Little exception, if the splitting factor is too low compared to the
    // acceptance angle, it's therefore possible to attain the splitting factor
    // without any first track. For the moment, we kill the particle, since the
    // russian roulette phenomena is applied and normally guaranties a
    // non-biased operation.
    if (nCalls >= fSplittingFactor) {
      fParticleChange.Initialize(*track);
      fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
      return &fParticleChange;
    }
    nCalls++;
  }

  // Initialisation of the information about the track.
  // We store the first gamma as the departure track, The first gamma is a
  // primary particle but with its weight modified , since it can be one of the
  // detected particles

  fParticleChange.Initialize(*track);
  fParticleChange.ProposeWeight(gammaWeight);
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
    initElectronTrack->SetWeight(gammaWeight);
    fParticleChange.AddSecondary(initElectronTrack);
  }

  processFinalState->Clear();
  castedProcessInitFinalState->Clear();

  // There is here the biasing process :
  //  Since G4VParticleChange class does not allow to retrieve scattered gamma
  //  information, we need to cast the type G4ParticleChangeForGamma to the
  //  G4VParticleChange object. We then call the process (biasWrapper(compt))
  //  fSplittingFactor -1 times (minus the number of call for the generation of
  //  the primary particle) to generate, at last, fSplittingFactor gamma
  //  according to the compton interaction process. If the gamma track is ok
  //  regarding the russian roulette algorithm (no russian roulette
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

  while (nCalls < splittingFactor) {
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
      if ((fRussianRoulette == true) && (theta > fMaxTheta)) {
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
          if (processGammaSplittedFinalState->GetNumberOfSecondaries() == 1) {
            G4Track *electronTrack =
                processGammaSplittedFinalState->GetSecondary(0);
            electronTrack->SetWeight(gammaWeight);
            fParticleChange.AddSecondary(electronTrack);
          }
        }
      }

      if ((fRussianRoulette == false) ||
          ((fRussianRoulette == true) && (theta <= fMaxTheta))) {
        G4Track *gammaTrack = new G4Track(*track);
        gammaTrack->SetWeight(gammaWeight);
        gammaTrack->SetKineticEnergy(energy);
        gammaTrack->SetMomentumDirection(momentum);
        gammaTrack->SetPosition(position);
        fParticleChange.AddSecondary(gammaTrack);
        if (processGammaSplittedFinalState->GetNumberOfSecondaries() == 1) {
          G4Track *electronTrack =
              processGammaSplittedFinalState->GetSecondary(0);
          electronTrack->SetWeight(gammaWeight);
          fParticleChange.AddSecondary(electronTrack);
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
