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
  fActions.insert("BeginOfRunActionMasterThread");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("PostUserTrackingAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");

  ResetRunAccumulators();
}

void GateDepositedChargeActor::ResetRunAccumulators() {
  fRunNominalCharge = 0.0;
  fRunDynamicCharge = 0.0;
  fRunNominalChargeSquared = 0.0;
  fRunDynamicChargeSquared = 0.0;
  fRunNumberOfEvents = 0;
}

void GateDepositedChargeActor::InitializeUserInfo(py::dict &user_info) {
  // Call the base class method to get user info parameters
  GateVActor::InitializeUserInfo(user_info);
}

void GateDepositedChargeActor::BeginOfRunActionMasterThread(int /*run_id*/) {
  // Reset the per-run accumulators on the master thread, before the worker
  // threads of this run start scoring.
  ResetRunAccumulators();
}

void GateDepositedChargeActor::BeginOfRunAction(const G4Run * /*run*/) {
  // Reset the thread-local per-run accumulators at the beginning of each run.
  auto &data = threadLocalData.Get();
  data.fEventNominalCharge = 0.0;
  data.fEventDynamicCharge = 0.0;
  data.fSumNominalCharge = 0.0;
  data.fSumNominalChargeSquared = 0.0;
  data.fSumDynamicCharge = 0.0;
  data.fSumDynamicChargeSquared = 0.0;
  data.fNumberOfEvents = 0;
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

void GateDepositedChargeActor::EndOfRunAction(const G4Run * /*run*/) {
  // Merge this worker's thread-local moments for the run that just ended and
  // reset the accumulators for the next run.
  G4AutoLock mutex(&GateDepositedChargeActorMutex);
  auto &data = threadLocalData.Get();
  fRunNominalCharge += data.fSumNominalCharge;
  fRunDynamicCharge += data.fSumDynamicCharge;
  fRunNominalChargeSquared += data.fSumNominalChargeSquared;
  fRunDynamicChargeSquared += data.fSumDynamicChargeSquared;
  fRunNumberOfEvents += data.fNumberOfEvents;

  data.fSumNominalCharge = 0.0;
  data.fSumNominalChargeSquared = 0.0;
  data.fSumDynamicCharge = 0.0;
  data.fSumDynamicChargeSquared = 0.0;
  data.fNumberOfEvents = 0;
}
