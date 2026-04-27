/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGammaFreeFlightOptrActor.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "G4BiasingProcessInterface.hh"
#include "G4EmParameters.hh"

GateGammaFreeFlightOptrActor::GateGammaFreeFlightOptrActor(py::dict &user_info)
    : GateVBiasOptrActor("GammaFreeFlightOperator", user_info, true) {
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation = nullptr;
  l.fIsFirstTime = true;
  fActions.insert("SteppingAction");
  // fActions.insert("EndOfRunAction");
  // fActions.insert("BeginOfEventAction");
}

GateGammaFreeFlightOptrActor::~GateGammaFreeFlightOptrActor() {
  // If we delete the fFreeFlightOperation, there are situations where
  // there is a seg fault after the simulation.
  // threadLocal_t &l = threadLocalData.Get();
  // delete l.fFreeFlightOperation;
}

void GateGammaFreeFlightOptrActor::InitializeCpp() {}

void GateGammaFreeFlightOptrActor::InitializeUserInfo(py::dict &user_info) {
  GateVBiasOptrActor::InitializeUserInfo(user_info);
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation =
      new GateGammaFreeFlightOptn("GammaFreeFlightOperation");
  l.fIsFirstTime = true;
  if (G4EmParameters::Instance()->GeneralProcessActive()) {
    Fatal("GeneralGammaProcess is active. Biasing can *not* work for "
          "GateVBiasOptrActor");
  }
}

void GateGammaFreeFlightOptrActor::StartTracking(const G4Track *track) {
  threadLocal_t &l = threadLocalData.Get();
  l.fIsFirstTime = true;
  l.fIsTrackValidForStep = true;
  l.fIsExcludedForStep = false;
  l.fLastStepNumber = -1;
  /* WARNING:
   the weight is reset to the initial particle weight when we start tracking.
   However, the weight of the particle can change between the "StartTracking"
   and the first time we see the particle in the tracked volume.
   The bool "fIsFirstTime" is used to reset the weight of the FF operation.
   */
}

G4VBiasingOperation *
GateGammaFreeFlightOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // should never be here
  DDD("ProposeNonPhysicsBiasingOperation: IF YOU SEE THIS, THERE IS A BUG");
  return nullptr;
}

G4VBiasingOperation *
GateGammaFreeFlightOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {

  threadLocal_t &l = threadLocalData.Get();

  if (l.fIsFirstTime) {
    l.fFreeFlightOperation->ResetInitialTrackWeight(track->GetWeight());
    l.fIsFirstTime = false;
  }

  // Kill tracks below cutoffs
  if (!IsTrackValid(track)) {
    l.fIsTrackValidForStep = false;
    l.fIsExcludedForStep = false;
    return nullptr;
  }

  // ----------------------------------------------------------------
  // Make the FF-vs-excluded decision HERE, ONCE, at the start of the step.
  // Store it in fIsExcludedForStep so ProposeFinalState uses the SAME answer.
  // This is mandatory: ProposeOccurence and ProposeFinalState must be
  // consistent for the same step (Geant4 rule, violation = BIAS.GEN.02).
  // ----------------------------------------------------------------
  const int currentStep = track->GetCurrentStepNumber();

  if (l.fLastStepNumber != currentStep) {
    // Only query the parallel navigator if this is a new step
    l.fIsExcludedForStep = IsInExcludedVolumeAcrossAllWorlds(track);
    l.fLastStepNumber = currentStep;
  }
  l.fIsTrackValidForStep = true;

  if (l.fIsExcludedForStep) {
    return nullptr;
  }

  return l.fFreeFlightOperation;
}

G4VBiasingOperation *
GateGammaFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {

  threadLocal_t &l = threadLocalData.Get();

  // ----------------------------------------------------------------
  // MUST be consistent with ProposeOccurenceBiasingOperation for this step.
  // We reuse the flags set there — no new navigator query here.
  // ----------------------------------------------------------------

  if (!l.fIsTrackValidForStep)
    return nullptr; // track is being killed
  if (l.fIsExcludedForStep)
    return nullptr; // normal physics, no FF

  return l.fFreeFlightOperation;
}

void GateGammaFreeFlightOptrActor::BeginOfEventAction(const G4Event *event) {
  // not used
}

void GateGammaFreeFlightOptrActor::SteppingAction(G4Step *step) {
  threadLocal_t &l = threadLocalData.Get();

  if (!l.fIsTrackValidForStep) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fIsTrackValidForStep = true;
  }
}

void GateGammaFreeFlightOptrActor::EndOfRunAction(const G4Run *) {
  // not used
}
