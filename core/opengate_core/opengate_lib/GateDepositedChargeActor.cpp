/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDepositedChargeActor.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

// Mutex to protect merging of thread-local charges into the total.
G4Mutex GateDepositedChargeActorMutex = G4MUTEX_INITIALIZER;

GateDepositedChargeActor::GateDepositedChargeActor(py::dict &user_info)
    : GateVActor(user_info, true) {

  // Geant4 callbacks need by this actor.
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("PostUserTrackingAction");
  fActions.insert("EndOfSimulationWorkerAction");

  // Initialize the total deposited charge to zero
  fDepositedNominalCharge = 0.0;
  fDepositedDynamicCharge = 0.0;
}

void GateDepositedChargeActor::InitializeUserInfo(py::dict &user_info) {
  // Call the base class method to get user info parameters
  GateVActor::InitializeUserInfo(user_info);
}

void GateDepositedChargeActor::StartSimulationAction() {
  // Reset the total deposited charges at the start of the simulation
  fDepositedNominalCharge = 0.0;
  fDepositedDynamicCharge = 0.0;
}

void GateDepositedChargeActor::BeginOfRunAction(const G4Run *run) {
  // Reset the thread-local charge accumulators at the begining of the first
  // run.
  if (run->GetRunID() == 0) {
    threadLocalData.Get().fNominalCharge = 0.0;
    threadLocalData.Get().fDynamicCharge = 0.0;
  }
}

void GateDepositedChargeActor::PreUserTrackingAction(const G4Track *track) {
  // Net deposited charge =
  //     + charge of particles dead in the attached volume
  //     - charge of particles born in the attached volume.

  const auto *vol = track->GetVolume();
  if (vol == nullptr || vol->GetName() != fAttachedToVolumeName)
    return;

  // Nominal charge is the charge of the particle definition.
  const double q_nominal = track->GetDefinition()->GetPDGCharge();

  // Dynamic (effective) charge at track birth.
  const double q_dynamic = track->GetDynamicParticle()->GetCharge();

  // Neutral particle -> do nothing
  if (q_nominal == 0.0 && q_dynamic == 0.0)
    return;

  auto &data = threadLocalData.Get();
  data.fNominalCharge -= q_nominal; // being born -> subtract nominal charge
  data.fDynamicCharge -= q_dynamic; // being born -> subtract dynamic charge
}

void GateDepositedChargeActor::PostUserTrackingAction(const G4Track *track) {
  const auto *vol = track->GetVolume();
  if (vol == nullptr || vol->GetName() != fAttachedToVolumeName)
    return;

  // Nominal charge is the charge of the particle definition.
  const double q_nominal = track->GetDefinition()->GetPDGCharge();

  // Dynamic (effective) charge at track death.
  const double q_dynamic = track->GetDynamicParticle()->GetCharge();

  // Neutral particle -> do nothing
  if (q_nominal == 0.0 && q_dynamic == 0.0)
    return;

  auto &data = threadLocalData.Get();
  data.fNominalCharge += q_nominal; // dying -> add nominal charge
  data.fDynamicCharge += q_dynamic; // dying -> add dynamic charge
}

void GateDepositedChargeActor::EndOfSimulationWorkerAction(
    const G4Run * /*lastRun*/) {
  // Accumulate the thread-local charges into the total deposited charge
  G4AutoLock mutex(
      &GateDepositedChargeActorMutex); // Lock the mutex to protect access to
                                       // the total deposited charge
  fDepositedNominalCharge += threadLocalData.Get().fNominalCharge;
  fDepositedDynamicCharge += threadLocalData.Get().fDynamicCharge;
}
