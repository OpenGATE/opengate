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
#include "GateOptnForceFreeFlight.h"
#include "G4BiasingProcessInterface.hh"
#include "G4ILawForceFreeFlight.hh"
#include "G4Step.hh"

// This operator is used to transport the particle without interaction, and then
// correct the weight of the particle
// according to the probablity for the photon to not interact within the matter.
// To do that, we use a GEANT4 modifed Interaction Law (G4ILawForceFreeFlight),
// which modify, for the biased process the probability for the interaction to
// occur :  Never. This occurence is called during the tracking for each step.
// Here the step is the largest possible, and one step correspond to the path of
// particle in the media.

GateOptnForceFreeFlight ::GateOptnForceFreeFlight(G4String name)
    : G4VBiasingOperation(name), fOperationComplete(true) {
  fForceFreeFlightInteractionLaw =
      new G4ILawForceFreeFlight("LawForOperation" + name);
}

GateOptnForceFreeFlight ::~GateOptnForceFreeFlight() {
  if (fForceFreeFlightInteractionLaw)
    delete fForceFreeFlightInteractionLaw;
}

const G4VBiasingInteractionLaw *
GateOptnForceFreeFlight ::ProvideOccurenceBiasingInteractionLaw(
    const G4BiasingProcessInterface *,
    G4ForceCondition &proposeForceCondition) {
  fOperationComplete = false;
  proposeForceCondition = Forced;
  return fForceFreeFlightInteractionLaw;
}

G4VParticleChange *GateOptnForceFreeFlight ::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &forceFinalState) {

  fParticleChange.Initialize(*track);
  forceFinalState = true;
  fCountProcess++;

  fProposedWeight *=
      fWeightChange[callingProcess->GetWrappedProcess()->GetProcessName()];

  if (fRussianRouletteForWeights) {
    G4int nbOfOrderOfMagnitude = std::log10(fInitialWeight / fMinWeight);

    if ((fProposedWeight < fMinWeight) ||
        ((fProposedWeight < 0.1 * fInitialWeight) &&
         (fNbOfRussianRoulette == nbOfOrderOfMagnitude - 1))) {
      fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
      fNbOfRussianRoulette = 0;
      return &fParticleChange;
    }

    if ((fProposedWeight < 0.1 * fInitialWeight) && (fCountProcess == 4)) {
      G4double probability = G4UniformRand();
      for (int i = 2; i <= nbOfOrderOfMagnitude; i++) {
        G4double RRprobability = 1 / std::pow(10, i);
        if (fProposedWeight * 1 / std::pow(10, fNbOfRussianRoulette) <
            10 * RRprobability * fMinWeight) {
          fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
          fNbOfRussianRoulette = 0;
          return &fParticleChange;
        }
        if ((fProposedWeight >= RRprobability * fInitialWeight) &&
            (fProposedWeight < 10 * RRprobability * fInitialWeight)) {
          if (probability > 10 * RRprobability) {
            fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
            fNbOfRussianRoulette = 0;
            return &fParticleChange;
          } else {
            fProposedWeight = fProposedWeight / (10 * RRprobability);
            fNbOfRussianRoulette = fNbOfRussianRoulette + i - 1;
          }
        }
      }
    }
  } else {
    if (fProposedWeight < fMinWeight) {
      fParticleChange.ProposeTrackStatus(G4TrackStatus::fStopAndKill);
      return &fParticleChange;
    }
  }
  fParticleChange.ProposeWeight(fProposedWeight);
  fOperationComplete = true;
  return &fParticleChange;
}

void GateOptnForceFreeFlight ::AlongMoveBy(
    const G4BiasingProcessInterface *callingProcess, const G4Step *,
    G4double weightChange)

{
  G4String processName = callingProcess->GetWrappedProcess()->GetProcessName();
  if (processName != "Rayl"){
    fWeightChange[processName] =
      weightChange;
  }
  else {
    fWeightChange[processName] = 1;
  }
}
