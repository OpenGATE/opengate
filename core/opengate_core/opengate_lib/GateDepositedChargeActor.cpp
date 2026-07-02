/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDepositedChargeActor.h"

// Mutex to protect merging of thread-local charges into the total.
G4Mutex GateDepositedChargeActorMutex = G4MUTEX_INITIALIZER;

GateDepositedChargeActor::GateDepositedChargeActor(py::dict &user_info)
    : GateVActor(user_info, true) {

  // Geant4 callbacks need by this actor.
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("PostUserTrackingAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfSimulationWorkerAction");

  // Initialize the merged accumulators to zero.
  fDepositedNominalCharge = 0.0;
  fDepositedDynamicCharge = 0.0;
  fDepositedNominalChargeSquared = 0.0;
  fDepositedDynamicChargeSquared = 0.0;
  fNumberOfEvents = 0;
}

void GateDepositedChargeActor::InitializeUserInfo(py::dict &user_info) {
  // Call the base class method to get user info parameters
  GateVActor::InitializeUserInfo(user_info);
}

void GateDepositedChargeActor::StartSimulationAction() {
  // Reset the merged accumulators at the start of the simulation
  fDepositedNominalCharge = 0.0;
  fDepositedDynamicCharge = 0.0;
  fDepositedNominalChargeSquared = 0.0;
  fDepositedDynamicChargeSquared = 0.0;
  fNumberOfEvents = 0;
}

void GateDepositedChargeActor::BeginOfRunAction(const G4Run *run) {
  // Reset the thread-local accumulators at the beginning of the first run.
  if (run->GetRunID() == 0) {
    auto &data = threadLocalData.Get();
    data.fEventNominalCharge = 0.0;
    data.fEventDynamicCharge = 0.0;
    data.fSumNominalCharge = 0.0;
    data.fSumNominalChargeSquared = 0.0;
    data.fSumDynamicCharge = 0.0;
    data.fSumDynamicChargeSquared = 0.0;
    data.fNumberOfEvents = 0;
  }
}

void GateDepositedChargeActor::BeginOfEventAction(const G4Event * /*event*/) {
  // Reset the per-event charge buffer.
  auto &data = threadLocalData.Get();
  data.fEventNominalCharge = 0.0;
  data.fEventDynamicCharge = 0.0;
}

void GateDepositedChargeActor::PreUserTrackingAction(const G4Track *track) {
  // Net deposited charge =
  //     + charge of particles dead in the attached volume
  //     - charge of particles born in the attached volume.

  const auto *vol = track->GetVolume();
  const auto *logical = (vol == nullptr) ? nullptr : vol->GetLogicalVolume();
  if (logical == nullptr || logical->GetName() != fAttachedToVolumeName)
    return;

  // Nominal charge is the charge of the particle definition.
  double q_nominal = track->GetDefinition()->GetPDGCharge();

  // Dynamic (effective) charge at track birth.
  double q_dynamic = track->GetDynamicParticle()->GetCharge();

  // Neutral particle -> do nothing
  if (q_nominal == 0.0 && q_dynamic == 0.0)
    return;

  // Get track weight and multiply charges to get the weighted contribution
  const double weight = track->GetWeight();
  q_nominal *= weight;
  q_dynamic *= weight;

  auto &data = threadLocalData.Get();
  data.fEventNominalCharge -=
      q_nominal; // being born -> subtract nominal charge
  data.fEventDynamicCharge -=
      q_dynamic; // being born -> subtract dynamic charge
}

void GateDepositedChargeActor::PostUserTrackingAction(const G4Track *track) {
  const auto *vol = track->GetVolume();
  const auto *logical = (vol == nullptr) ? nullptr : vol->GetLogicalVolume();
  if (logical == nullptr || logical->GetName() != fAttachedToVolumeName)
    return;

  // Nominal charge is the charge of the particle definition.
  double q_nominal = track->GetDefinition()->GetPDGCharge();

  // Dynamic (effective) charge at track death.
  double q_dynamic = track->GetDynamicParticle()->GetCharge();

  // Neutral particle -> do nothing
  if (q_nominal == 0.0 && q_dynamic == 0.0)
    return;

  // Get track weight and multiply charges to get the weighted contribution
  const double weight = track->GetWeight();
  q_nominal *= weight;
  q_dynamic *= weight;

  auto &data = threadLocalData.Get();
  data.fEventNominalCharge += q_nominal; // dying -> add nominal charge
  data.fEventDynamicCharge += q_dynamic; // dying -> add dynamic charge
}

void GateDepositedChargeActor::EndOfEventAction(const G4Event * /*event*/) {
  // Fold the per-event net charge into the running first and second moments.
  auto &data = threadLocalData.Get();

  const double xn = data.fEventNominalCharge;
  const double xd = data.fEventDynamicCharge;

  data.fSumNominalCharge += xn;
  data.fSumNominalChargeSquared += xn * xn;
  data.fSumDynamicCharge += xd;
  data.fSumDynamicChargeSquared += xd * xd;
  data.fNumberOfEvents += 1;
}

void GateDepositedChargeActor::EndOfSimulationWorkerAction(
    const G4Run * /*lastRun*/) {
  // Accumulate the thread-local moments into the merged accumulators.
  G4AutoLock mutex(&GateDepositedChargeActorMutex);
  auto &data = threadLocalData.Get();
  fDepositedNominalCharge += data.fSumNominalCharge;
  fDepositedDynamicCharge += data.fSumDynamicCharge;
  fDepositedNominalChargeSquared += data.fSumNominalChargeSquared;
  fDepositedDynamicChargeSquared += data.fSumDynamicChargeSquared;
  fNumberOfEvents += data.fNumberOfEvents;
}
