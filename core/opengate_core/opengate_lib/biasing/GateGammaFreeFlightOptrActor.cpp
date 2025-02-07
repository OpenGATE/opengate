/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGammaFreeFlightOptrActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "G4BiasingProcessInterface.hh"

GateGammaFreeFlightOptrActor::GateGammaFreeFlightOptrActor(py::dict &user_info)
    : GateVBiasOptrActor("GammaFreeFlightOperator", user_info, false) {
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation = nullptr;
}

GateGammaFreeFlightOptrActor::~GateGammaFreeFlightOptrActor() {
  threadLocal_t &l = threadLocalData.Get();
  delete l.fFreeFlightOperation;
}

void GateGammaFreeFlightOptrActor::InitializeCpp() {}

void GateGammaFreeFlightOptrActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation =
      new G4BOptnForceFreeFlight("GammaFreeFlightOperator");
}

void GateGammaFreeFlightOptrActor::StartTracking(const G4Track *track) {
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation->ResetInitialTrackWeight(track->GetWeight());
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
  return l.fFreeFlightOperation;
}

G4VBiasingOperation *
GateGammaFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  return callingProcess->GetCurrentOccurenceBiasingOperation();
}
