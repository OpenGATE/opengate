/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGammaFreeFlightOptn.h"
#include "../GateHelpers.h"
#include "G4BiasingProcessInterface.hh"

GateGammaFreeFlightOptn::GateGammaFreeFlightOptn(const G4String &name)
    : G4VBiasingOperation(name) {
  fForceFreeFlightInteractionLaw =
      new G4ILawForceFreeFlight("LawForOperation" + name);
}

GateGammaFreeFlightOptn::~GateGammaFreeFlightOptn() {
  delete fForceFreeFlightInteractionLaw;
}

const G4VBiasingInteractionLaw *
GateGammaFreeFlightOptn::ProvideOccurenceBiasingInteractionLaw(
    const G4BiasingProcessInterface *,
    G4ForceCondition &proposeForceCondition) {
  fOperationComplete = false;
  proposeForceCondition = Forced;
  // proposeForceCondition = Condition; // BUG
  // proposeForceCondition = NotForced; // idem
  // proposeForceCondition = StronglyForced; // idem
  // proposeForceCondition = ExclusivelyForced; // BUG
  return fForceFreeFlightInteractionLaw;
}

G4double GateGammaFreeFlightOptn::DistanceToApplyOperation(const G4Track *,
                                                           G4double,
                                                           G4ForceCondition *) {
  return DBL_MAX;
}

G4VParticleChange *
GateGammaFreeFlightOptn::GenerateBiasingFinalState(const G4Track *,
                                                   const G4Step *) {
  return nullptr;
}

void GateGammaFreeFlightOptn::ResetInitialTrackWeight(G4double w) {
  fProposedWeight = w;
}

G4VParticleChange *GateGammaFreeFlightOptn::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &forceFinalState) {

  // -- At the beginning of the operation, fOperationComplete is false.
  // -- We enter this block only ONCE per step, on the first call
  // -- to ApplyFinalStateBiasing by any of the biased processes.
  if (!fOperationComplete) {

    // -- Loop through ALL stored survival probabilities from ALL biased
    // -- processes that were collected by AlongMoveBy.
    for (auto const &[process_subtype, weight_change] : fProcessTypeToWeight) {
      fProposedWeight *= weight_change;
    }

    // -- Clear the map for the next step and set the flag to prevent re-entry.
    fProcessTypeToWeight.clear();
    fOperationComplete = true;
  }

  // -- For all calls (the first and later ones for this step),
  // -- propose the same, final, correctly calculated weight.
  fParticleChange.Initialize(*track);
  fParticleChange.ProposeWeight(fProposedWeight);
  forceFinalState = true;

  return &fParticleChange;
}

void GateGammaFreeFlightOptn::AlongMoveBy(
    const G4BiasingProcessInterface *callingProcess, const G4Step *step,
    G4double weightChange) {
  fProcessTypeToWeight[callingProcess->GetWrappedProcess()
                           ->GetProcessSubType()] = weightChange;
}
