/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateBremsstrahlungSplittingOptrActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "G4BiasingProcessInterface.hh"
#include "GateBremsstrahlungSplittingOptn.h"

GateBremsstrahlungSplittingOptrActor::GateBremsstrahlungSplittingOptrActor(
    py::dict &user_info)
    : GateVBiasOptrActor("BremSplittingOperator", user_info, false) {
  fActions.insert("BeginOfRunAction");
  fActions.insert("PreUserTrackingAction");
  fSplittingFactor = 1;
  fBiasOnlyOnce = false;
  fBiasPrimaryOnly = false;
  fNInteractions = 0;
  fBremSplittingOperation = nullptr;
}

void GateBremsstrahlungSplittingOptrActor::InitializeUserInfo(
    py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVBiasOptrActor::InitializeUserInfo(user_info);
  fSplittingFactor = DictGetInt(user_info, "splitting_factor");
  fBiasPrimaryOnly = DictGetBool(user_info, "bias_primary_only");
  fBiasOnlyOnce = DictGetBool(user_info, "bias_only_once");
}

void GateBremsstrahlungSplittingOptrActor::InitializeCpp() {
  fBremSplittingOperation =
      new GateBremsstrahlungSplittingOptn("BremSplittingOperation");
}

void GateBremsstrahlungSplittingOptrActor::StartRun() {
  fBremSplittingOperation->SetSplittingFactor(fSplittingFactor);
  const G4LogicalVolume *biasingVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  AttachTo(biasingVolume);
  DDD(biasingVolume->GetName());
  DDD(fAttachedToVolumeName);
}

void GateBremsstrahlungSplittingOptrActor::StartTracking(const G4Track *track) {
  // reset the number of times the brem. splitting was applied:
  fNInteractions = 0;
}

G4VBiasingOperation *
GateBremsstrahlungSplittingOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
  return nullptr;
}

G4VBiasingOperation *
GateBremsstrahlungSplittingOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
  return nullptr;
}

G4VBiasingOperation *
GateBremsstrahlungSplittingOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // -- Check if biasing of primary particle only is requested. If so, and
  // -- if particle is not a primary one, don't ask for biasing:
  if (fBiasPrimaryOnly && (track->GetParentID() != 0))
    return nullptr;
  // -- Check if brem. splitting should be applied only once to the track,
  // -- and if so, and if brem. splitting already occurred, don't ask for
  // biasing:
  if (fBiasOnlyOnce && (fNInteractions > 0))
    return nullptr;

  // -- Count the number of times the brem. splitting is applied:
  fNInteractions++;
  // -- Return the brem. splitting operation:
  return fBremSplittingOperation;
}
