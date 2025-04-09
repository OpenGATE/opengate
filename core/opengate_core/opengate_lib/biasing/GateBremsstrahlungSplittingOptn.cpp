/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateBremsstrahlungSplittingOptn.h"
#include "G4BiasingProcessInterface.hh"
#include "G4ParticleChangeForLoss.hh"

GateBremsstrahlungSplittingOptn::GateBremsstrahlungSplittingOptn(
    const G4String &name)
    : G4VBiasingOperation(name), fSplittingFactor(1) {}

const G4VBiasingInteractionLaw *
GateBremsstrahlungSplittingOptn::ProvideOccurenceBiasingInteractionLaw(
    const G4BiasingProcessInterface *, G4ForceCondition &) {
  return nullptr;
}

void GateBremsstrahlungSplittingOptn::SetSplittingFactor(
    G4int splittingFactor) {
  fSplittingFactor = splittingFactor;
}

G4int GateBremsstrahlungSplittingOptn::GetSplittingFactor() const {
  return fSplittingFactor;
}

G4double GateBremsstrahlungSplittingOptn::DistanceToApplyOperation(
    const G4Track *, G4double, G4ForceCondition *) {
  return DBL_MAX;
}

G4VParticleChange *
GateBremsstrahlungSplittingOptn::GenerateBiasingFinalState(const G4Track *,
                                                           const G4Step *) {
  return 0;
}

G4VParticleChange *GateBremsstrahlungSplittingOptn::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {
  // -- Collect brem. process (wrapped process) final state:
  G4VParticleChange *processFinalState =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);

  // -- if no splitting requested, let the brem. process to return directly its
  // -- generated final state:
  if (fSplittingFactor == 1)
    return processFinalState;

  // -- a special case here: the brem. process corrects for cross-section change
  // -- over the step due to energy loss by sometimes "abandoning" the
  // interaction,
  // -- returning an unchanged incoming electron/positron.
  // -- We respect this correction, and if no secondary is produced, its means
  // this
  // -- case is happening:
  if (processFinalState->GetNumberOfSecondaries() == 0)
    return processFinalState;

  // -- Now start the biasing:
  // --   - the electron state will be taken as the first one produced by the
  // brem.
  // --     process, hence the one stored in above processFinalState particle
  // change.
  // --     This state will be stored in our fParticleChange object.
  // --   - the photon accompanying the electron will be stored also this way.
  // --   - we will then do fSplittingFactor - 1 call to the brem. process to
  // collect
  // --     fSplittingFactor - 1 additional gammas. All these will be stored in
  // our
  // --     fParticleChange object.

  // -- We called the brem. process above. Its concrete particle change is
  // indeed
  // -- a "G4ParticleChangeForLoss" object. We cast this particle change to
  // access
  // -- methods of the concrete G4ParticleChangeForLoss type:
  auto *actualParticleChange =
      dynamic_cast<G4ParticleChangeForLoss *>(processFinalState);

  fParticleChange.Initialize(*track);

  // -- Store electron final state:
  fParticleChange.ProposeTrackStatus(actualParticleChange->GetTrackStatus());
  fParticleChange.ProposeEnergy(
      actualParticleChange->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      actualParticleChange->GetProposedMomentumDirection());

  // -- Now deal with the gamma's:
  // -- their common weight:
  G4double gammaWeight = track->GetWeight() / fSplittingFactor;

  // -- inform we will have fSplittingFactor gamma's:
  fParticleChange.SetNumberOfSecondaries(fSplittingFactor);

  // -- inform we take care of secondaries weight (otherwise these
  // -- secondaries are by default given the primary weight).
  fParticleChange.SetSecondaryWeightByProcess(true);

  // -- Store first gamma:
  G4Track *gammaTrack = actualParticleChange->GetSecondary(0);
  gammaTrack->SetWeight(gammaWeight);
  fParticleChange.AddSecondary(gammaTrack);
  // -- and clean-up the brem. process particle change:
  actualParticleChange->Clear();

  // -- now start the fSplittingFactor-1 calls to the brem. process to store
  // each
  // -- related gamma:
  G4int nCalls = 1;
  while (nCalls < fSplittingFactor) {
    // ( note: we don't need to cast to actual type here, as methods for
    // accessing
    //   secondary particles are from base class G4VParticleChange )
    processFinalState =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    if (processFinalState->GetNumberOfSecondaries() == 1) {
      gammaTrack = processFinalState->GetSecondary(0);
      gammaTrack->SetWeight(gammaWeight);
      fParticleChange.AddSecondary(gammaTrack);
      nCalls++;
    }
    // -- very rare special case: we ignore for now.
    else if (processFinalState->GetNumberOfSecondaries() > 1) {
      for (G4int i = 0; i < processFinalState->GetNumberOfSecondaries(); i++)
        delete processFinalState->GetSecondary(i);
    }
    processFinalState->Clear();
  }

  // -- we are done:
  return &fParticleChange;
}
