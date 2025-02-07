/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateComptonSplittingFreeFlightOptn.h"
#include "../GateHelpers.h"
#include "G4BiasingProcessInterface.hh"
#include "G4ParticleChangeForGamma.hh"
#include "G4RunManager.hh"

GateComptonSplittingFreeFlightOptn::GateComptonSplittingFreeFlightOptn(
    const G4String &name)
    : G4VBiasingOperation(name), fSplittingFactor(1) {
  fAAManager = nullptr;
}

const G4VBiasingInteractionLaw *
GateComptonSplittingFreeFlightOptn::ProvideOccurenceBiasingInteractionLaw(
    const G4BiasingProcessInterface *, G4ForceCondition &) {
  return nullptr;
}

G4double GateComptonSplittingFreeFlightOptn::DistanceToApplyOperation(
    const G4Track *, G4double, G4ForceCondition *) {
  return DBL_MAX;
}

G4VParticleChange *
GateComptonSplittingFreeFlightOptn::GenerateBiasingFinalState(const G4Track *,
                                                              const G4Step *) {
  return nullptr;
}

void GateComptonSplittingFreeFlightOptn::SetSplittingFactor(
    const G4int splittingFactor) {
  fSplittingFactor = splittingFactor;
}

void GateComptonSplittingFreeFlightOptn::InitializeAAManager(
    py::dict user_info) {
  fAAManager = new GateAcceptanceAngleTesterManager();
  fAAManager->Initialize(user_info, true);
}

G4VParticleChange *GateComptonSplittingFreeFlightOptn::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {
  // const double weight = track->GetWeight() / fSplittingFactor;
  //  FIXME: no need to set the splitting weight because set by
  //  SetSecondaryWeightByProcess ?
  const double weight = track->GetWeight() / fSplittingFactor;
  const auto position = step->GetPostStepPoint()->GetPosition();

  // DDD(track->GetWeight());

  // This is the scattered Gamma
  auto *processFinalStateForGamma =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
  const auto fs_fg =
      dynamic_cast<G4ParticleChangeForGamma *>(processFinalStateForGamma);
  fParticleChange.Initialize(*track);
  fParticleChange.ProposeTrackStatus(fs_fg->GetTrackStatus());
  fParticleChange.ProposeEnergy(fs_fg->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      fs_fg->GetProposedMomentumDirection());

  // Copied from G4: "inform we take care of secondaries weight (otherwise these
  // secondaries are by default given the primary weight)."
  fParticleChange.SetSecondaryWeightByProcess(
      true); // FIXME, important, unclear
  // fParticleChange.SetSecondaryWeightByProcess(false); // FIXME, important,
  // unclear
  fParticleChange.SetParentWeightByProcess(true); // FIXME ??

  // fParticleChange.SetNumberOfSecondaries(fSplittingFactor);
  // DDD(fParticleChange.GetWeight());
  // DDD(fParticleChange.GetParentWeight());
  // fParticleChange.ProposeWeight(); /// FIXME

  // split gammas
  fAAManager->StartAcceptLoop();
  int nb_of_secondaries = 0;
  std::vector<G4Track *> secondary_tracks;
  for (auto i = 0; i < fSplittingFactor; i++) {
    auto *processFinalState =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    const auto fs = dynamic_cast<G4ParticleChangeForGamma *>(processFinalState);
    auto momentum = fs->GetProposedMomentumDirection();

    // AA ?
    if (!fAAManager->TestIfAccept(position, momentum)) {
      continue;
    }

    // Create a new track with another gamma
    const auto energy = fs->GetProposedKineticEnergy();
    auto gammaTrack = new G4Track(*track);
    gammaTrack->SetWeight(weight);
    gammaTrack->SetKineticEnergy(energy);
    gammaTrack->SetMomentumDirection(momentum);
    gammaTrack->SetPosition(position);

    // consider this gamma as a secondary
    nb_of_secondaries++;
    secondary_tracks.push_back(gammaTrack);

    // FIXME secondaries electrons ? (ignored for now)
  }

  // fParticleChange->ProposeParentWeight(initialWeight);

  // Add secondaries
  fParticleChange.SetNumberOfSecondaries(nb_of_secondaries);
  for (const auto gammaTrack : secondary_tracks)
    fParticleChange.AddSecondary(gammaTrack);

  return &fParticleChange;
}
