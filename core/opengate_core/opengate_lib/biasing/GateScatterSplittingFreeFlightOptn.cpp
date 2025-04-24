/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateScatterSplittingFreeFlightOptn.h"
#include "../GateHelpers.h"
#include "G4BiasingProcessInterface.hh"
#include "G4EmParameters.hh"
#include "G4GammaGeneralProcess.hh"
#include "G4ParticleChangeForGamma.hh"
#include "G4RunManager.hh"

GateScatterSplittingFreeFlightOptn::GateScatterSplittingFreeFlightOptn(
    const G4String &name, double *nbTracks)
    : G4VBiasingOperation(name), fSplittingFactor(1) {
  fAAManager = nullptr;
  fNbTracks = nbTracks;
  fUserTrackInformation = nullptr;
}

const G4VBiasingInteractionLaw *
GateScatterSplittingFreeFlightOptn::ProvideOccurenceBiasingInteractionLaw(
    const G4BiasingProcessInterface *, G4ForceCondition &) {
  return nullptr;
}

G4double GateScatterSplittingFreeFlightOptn::DistanceToApplyOperation(
    const G4Track *, G4double, G4ForceCondition *) {
  return DBL_MAX;
}

G4VParticleChange *
GateScatterSplittingFreeFlightOptn::GenerateBiasingFinalState(const G4Track *,
                                                              const G4Step *) {
  return nullptr;
}

void GateScatterSplittingFreeFlightOptn::SetSplittingFactor(
    const G4int splittingFactor) {
  fSplittingFactor = splittingFactor;
}

void GateScatterSplittingFreeFlightOptn::InitializeAAManager(
    const py::dict &user_info) {
  fAAManager = new GateAcceptanceAngleManager();
  fAAManager->Initialize(user_info, true);

  if (G4EmParameters::Instance()->GeneralProcessActive()) {
    Fatal("GeneralGammaProcess is not active. . This do *not* work for "
          "ScatterSplittingFreeFlight");
  }
}

G4VParticleChange *GateScatterSplittingFreeFlightOptn::ApplyFinalStateBiasing(
    const G4BiasingProcessInterface *callingProcess, const G4Track *track,
    const G4Step *step, G4bool &) {

  // This is the initial scattered Gamma
  auto *final_state =
      callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
  auto particle_change = dynamic_cast<G4ParticleChangeForGamma *>(final_state);

  const auto position = step->GetPostStepPoint()->GetPosition();
  fParticleChange.Initialize(*track);
  fParticleChange.ProposeTrackStatus(particle_change->GetTrackStatus());
  fParticleChange.ProposeEnergy(particle_change->GetProposedKineticEnergy());
  fParticleChange.ProposeMomentumDirection(
      particle_change->GetProposedMomentumDirection());

  // Copied from G4: "inform we take care of secondaries weight (otherwise these
  // secondaries are by default given the primary weight)."
  fParticleChange.SetSecondaryWeightByProcess(true); // 'true' is needed
  // fParticleChange.SetParentWeightByProcess(true);   // unsure ?

  // set the weight for the split track and the position
  const double weight = track->GetWeight() / fSplittingFactor;

  // delete secondaries to avoid memory leak
  for (auto j = 0; j < final_state->GetNumberOfSecondaries(); j++) {
    const auto *sec = final_state->GetSecondary(j);
    delete sec;
  }
  particle_change->Clear(); // FIXME useful ? like in brem ?

  // Loop to split Compton gammas
  fAAManager->StartAcceptLoop();
  for (auto i = 0; i < fSplittingFactor; i++) {
    double energy = 0;
    final_state =
        callingProcess->GetWrappedProcess()->PostStepDoIt(*track, *step);
    particle_change = dynamic_cast<G4ParticleChangeForGamma *>(final_state);

    // delete secondaries to avoid memory leak
    for (auto j = 0; j < final_state->GetNumberOfSecondaries(); j++) {
      const auto *sec = final_state->GetSecondary(j);
      delete sec;
    }

    // Angular Acceptance rejection, we ignore the secondary if not ok
    const auto momentum = particle_change->GetProposedMomentumDirection();
    if (!fAAManager->TestIfAccept(position, momentum)) {
      continue;
    }

    energy = particle_change->GetProposedKineticEnergy();
    if (energy > 0) {
      // Create a new track with another gamma (free by G4)
      const auto gammaTrack = new G4Track(*track);
      gammaTrack->SetWeight(weight);
      gammaTrack->SetMomentumDirection(momentum);
      gammaTrack->SetKineticEnergy(energy);
      gammaTrack->SetPosition(position);
      // FIXME time ? polarization ?
      gammaTrack->SetTrackStatus(particle_change->GetTrackStatus()); // needed ?

      // Seems that this pointer is free by G4
      fUserTrackInformation = new GateUserTrackInformation();
      fUserTrackInformation->SetGateTrackInformation(fActor, true);
      gammaTrack->SetUserInformation(fUserTrackInformation);

      // Add the track in the stack
      fParticleChange.AddSecondary(gammaTrack);
    }

    particle_change->Clear(); // FIXME like in brem
  }

  // Count the nb of secondaries
  (*fNbTracks) += fParticleChange.GetNumberOfSecondaries();

  return &fParticleChange;
}
