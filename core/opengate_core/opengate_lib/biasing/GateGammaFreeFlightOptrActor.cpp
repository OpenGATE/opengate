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
}

void GateGammaFreeFlightOptrActor::StartTracking(const G4Track *track) {
  threadLocal_t &l = threadLocalData.Get();
  l.fIsFirstTime = true;
  l.fIsTrackValidForStep = true;
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
  // For this particle, at this location, should we apply 'FreeFlight' biasing?
  // return l.fFreeFlightOperation => use Free Flight VRT for this step
  // return nullptr => not biased, use standard physics

  threadLocal_t &l = threadLocalData.Get();
  if (l.fIsFirstTime) {
    l.fFreeFlightOperation->ResetInitialTrackWeight(track->GetWeight());
    l.fIsFirstTime = false;
  }
  // Is it a valid particle?
  if (!IsTrackValid(track)) {
    l.fIsTrackValidForStep = false;
    return nullptr;
  }
  l.fIsTrackValidForStep = true;

  // Go for FF
  return l.fFreeFlightOperation;
}

G4VBiasingOperation *
GateGammaFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  threadLocal_t &l = threadLocalData.Get();
  // Was it valid at the start of the step?
  if (!l.fIsTrackValidForStep)
    return nullptr;
  // Go for FF
  return l.fFreeFlightOperation;
}

void GateGammaFreeFlightOptrActor::BeginOfEventAction(const G4Event *event) {
  // not used
}

void GateGammaFreeFlightOptrActor::SteppingAction(G4Step *step) {
  threadLocal_t &l = threadLocalData.Get();
  // Was it valid at the start of the step?
  // Note: it only applies for FF particles, not analog ones

  if (!l.fIsTrackValidForStep) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fIsTrackValidForStep = true;
  }
}

void GateGammaFreeFlightOptrActor::EndOfRunAction(const G4Run *) {
  // not used
}
