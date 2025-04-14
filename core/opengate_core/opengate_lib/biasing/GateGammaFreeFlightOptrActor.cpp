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
}

GateGammaFreeFlightOptrActor::~GateGammaFreeFlightOptrActor() {
  threadLocal_t &l = threadLocalData.Get();
  delete l.fFreeFlightOperation;
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
  l.fFreeFlightOperation->ResetInitialTrackWeight(track->GetWeight());
  /* WARNING:
   the weight is reset to the initial particle weight when we start tracking.
   However, the weight of the particle can change between the "StartTracking"
   and the first time we see the particle in the tracked volume.
   The bool "fIsFirstTime" is used to reset the weight of the FF operation.
   */
}

G4VBiasingOperation *
GateGammaFreeFlightOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
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
  return l.fFreeFlightOperation;
}

G4VBiasingOperation *
GateGammaFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  threadLocal_t &l = threadLocalData.Get();
  return l.fFreeFlightOperation;
}
