/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateOptrFreeFlightActor.h"
#include "G4BiasingProcessInterface.hh"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

GateOptrFreeFlightActor::GateOptrFreeFlightActor(py::dict &user_info)
    : G4VBiasingOperator("FreeFlightOperator"), GateVActor(user_info, true) {
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation = nullptr;
}

GateOptrFreeFlightActor::~GateOptrFreeFlightActor() {
  threadLocal_t &l = threadLocalData.Get();
  delete l.fFreeFlightOperation;
}

void GateOptrFreeFlightActor::InitializeCpp() {}

void GateOptrFreeFlightActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
}

void GateOptrFreeFlightActor::Configure() {
  auto *biasedVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  AttachAllLogicalDaughtersVolumes(biasedVolume);
}

void GateOptrFreeFlightActor::ConfigureForWorker() {
  auto *biasedVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  AttachAllLogicalDaughtersVolumes(biasedVolume);
  // set to null, will be created the first time in StartTracking
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation = nullptr;
}

void GateOptrFreeFlightActor::AttachAllLogicalDaughtersVolumes(
    G4LogicalVolume *volume) {
  AttachTo(volume);
  // FIXME mother class + user option
  G4int nbOfDaughters = volume->GetNoDaughters();
  if (nbOfDaughters > 0) {
    for (int i = 0; i < nbOfDaughters; i++) {
      G4LogicalVolume *logicalDaughtersVolume =
          volume->GetDaughter(i)->GetLogicalVolume();
      AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
    }
  }
}

void GateOptrFreeFlightActor::StartTracking(const G4Track *track) {
  threadLocal_t &l = threadLocalData.Get();
  if (l.fFreeFlightOperation == nullptr) {
    l.fFreeFlightOperation = new G4BOptnForceFreeFlight("freeFlightOperation");
  }
  l.fFreeFlightOperation->ResetInitialTrackWeight(1.0);
}

G4VBiasingOperation *GateOptrFreeFlightActor::ProposeNonPhysicsBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
  return nullptr;
}

G4VBiasingOperation *GateOptrFreeFlightActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  threadLocal_t &l = threadLocalData.Get();
  return l.fFreeFlightOperation;
}

G4VBiasingOperation *GateOptrFreeFlightActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  return callingProcess->GetCurrentOccurenceBiasingOperation();
}

void GateOptrFreeFlightActor::PreUserTrackingAction(const G4Track *track) {
  StartTracking(track);
}
