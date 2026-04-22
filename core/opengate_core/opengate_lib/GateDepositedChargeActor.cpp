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
  fActions.insert("SteppingAction");
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

void GateDepositedChargeActor::SteppingAction(G4Step *step) {
  // Net deposited charge =
  //     + charge of particles entering the attached volume
  //     - charge of particles leaving the attached volume.

  // Step is entering the attached volume
  const bool entering =
      step->GetPreStepPoint()->GetStepStatus() == fGeomBoundary;

  // Step is exiting the attached volume
  const bool exiting = IsStepExitingAttachedVolume(step);

  // Entering nor exiting -> do nothing
  if (!entering && !exiting)
    return;

  // Else:
  //   Get the charge of the particle
  const auto *track = step->GetTrack();

  // Nominal charge is the charge of the particle definition.
  const double q_nominal = track->GetDefinition()->GetPDGCharge();

  // Dynamic (effective) charge at the moment of the boundary crossing.
  // Use the pre-step charge so that charge-changing interactions
  // during the step don't affect the crossing value.
  const double q_dynamic = step->GetPreStepPoint()->GetCharge();

  //   Neutral particle -> do nothing
  if (q_nominal == 0.0 && q_dynamic == 0.0)
    return;

  //   Update the thread-local charge accumulator
  auto &data = threadLocalData.Get();
  if (entering) {
    data.fNominalCharge += q_nominal; // entering -> add nominal charge
    data.fDynamicCharge += q_dynamic; // entering -> add dynamic charge
  }
  if (exiting) {
    data.fNominalCharge -= q_nominal; // exiting  -> subtract nominal charge
    data.fDynamicCharge -= q_dynamic; // exiting  -> subtract dynamic charge
  }
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
