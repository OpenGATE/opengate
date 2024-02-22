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
#include "G4TrackStatus.hh"

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
  const G4ParticleDefinition *particleDefinition =
      step->GetTrack()->GetDefinition();

  G4int nCalls = 0;
  G4int splittingFactor = ceil(fSplittingFactor);
  G4double survivalProbabilitySplitting =
      1 - (splittingFactor - fSplittingFactor) / splittingFactor;
  G4bool isRightAngle = false;
  G4double gammaWeight = track->GetWeight() / fSplittingFactor;
  G4int nbSecondaries = 0;
  G4VParticleChange *processFinalState = nullptr;
  G4ParticleChangeForGamma *castedProcessInitFinalState = nullptr;

  while (isRightAngle == false) {
    processFinalState =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    // In case we don't want to split (a bit faster)
    if (fSplittingFactor == 1 && fRussianRoulette == false)
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

      // If the russian roulette is activated, we need to initialize the track
      // with a primary particle which have the right angle That's why nCall is
      // also incremented here, to avoid any bias in te number of gamma
      // generated
      if ((fRussianRoulette == true) && (theta > fMaxTheta)) {
        G4double probability = G4UniformRand();
        if (probability < 1 / fSplittingFactor) {

          gammaWeight = track->GetWeight();
          isRightAngle = true;
        }
      }

      if ((fRussianRoulette == false) ||
          ((fRussianRoulette == true) && (theta <= fMaxTheta))) {
        G4double probability = G4UniformRand();
        isRightAngle = true;
      }
    }
    nCalls++;

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

  fParticleChange.SetNumberOfSecondaries(fSplittingFactor);
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
  gammaWeight = track->GetWeight() / fSplittingFactor;

  // There is here the biasing process :
  //  Since G4VParticleChange classe does not allow to retrieve scattered gamma
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
  //  account by the MC simulation. PS : Normally G4VParticleChange allows users
  //  to directly retrieve the track of the secondary particles generated, track
  //  you can then add to the primary particle, but since the gamma from the
  //  compton effect is not a new gamma for GEANT4, you cant't use this
  //  function, and you need to generate a track from the different observables
  //  of the scattered gamma PPS : The first gamma is then the primary particle,
  //  but all the other splitted particle (electron of course AND gamma) must be
  //  considered as secondary particles, even though generated gamma will not be
  //  cut by the applied cut.

  while (nCalls < splittingFactor) {

    G4VParticleChange *processGammaSplittedFinalState =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    G4ParticleChangeForGamma *castedProcessGammaSplittedFinalState =
        (G4ParticleChangeForGamma *)processGammaSplittedFinalState;
    const G4ThreeVector momentum =
        castedProcessGammaSplittedFinalState->GetProposedMomentumDirection();
    G4double energy =
        castedProcessGammaSplittedFinalState->GetProposedKineticEnergy();
    G4DynamicParticle *split_particle =
        new G4DynamicParticle(particleDefinition, position, energy);
    G4Track *GammaTrack = new G4Track(split_particle, globalTime, position);
    GammaTrack->SetMomentumDirection(momentum);
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
          // wil have a 1/split probability to survive with a final weight of
          // Initial weights * 1/split * split = Initial weight
          GammaTrack->SetWeight(track->GetWeight());
          fParticleChange.AddSecondary(GammaTrack);
          if (processGammaSplittedFinalState->GetNumberOfSecondaries() == 1) {
            G4Track *electronTrack =
                processGammaSplittedFinalState->GetSecondary(0);
            electronTrack->SetWeight(track->GetWeight());
            fParticleChange.AddSecondary(electronTrack);
          }
        }
      }

      if ((fRussianRoulette == false) ||
          ((fRussianRoulette == true) && (theta <= fMaxTheta))) {
        G4double probability = G4UniformRand();
        GammaTrack->SetWeight(gammaWeight);
        fParticleChange.AddSecondary(GammaTrack);
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
  }
  return &fParticleChange;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
