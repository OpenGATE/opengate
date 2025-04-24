/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVBiasOptrActor.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "G4LogicalVolumeStore.hh"
#include "G4RunManager.hh"
#include <vnl_matrix.h>

GateVBiasOptrActor::GateVBiasOptrActor(const std::string &name,
                                       py::dict &user_info, const bool MT_ready)
    : G4VBiasingOperator(name), GateVActor(user_info, MT_ready) {
  // It seems that it is needed in MT (see PreUserTrackingAction)
  fActions.insert("PreUserTrackingAction");
  // SteppingAction for killing when the weight is too low
  fActions.insert("SteppingAction");
  fMinimalWeight = std::numeric_limits<double>::min(); // around 2.22507e-308
}

std::vector<G4VBiasingOperator *> &
GateVBiasOptrActor::GetNonConstBiasingOperators() {
  // WARNING PEGI 18: Don't look at it if you are sensitive and have a pure
  // heart.
  auto &operators = const_cast<std::vector<G4VBiasingOperator *> &>(
      G4VBiasingOperator::GetBiasingOperators());
  return operators;
}

void GateVBiasOptrActor::ClearOperators() {
  GetNonConstBiasingOperators().clear();
}

void GateVBiasOptrActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fMinimalWeight = DictGetDouble(user_info, "minimal_weight");
  if (fMinimalWeight < 0) {
    fMinimalWeight = std::numeric_limits<double>::min(); // around 2.22507e-308
  }

  fIgnoredVolumes = DictGetVecStr(user_info, "ignored_volumes");

  // check ignored volumes
  for (auto &name : fIgnoredVolumes) {
    const auto *v = G4LogicalVolumeStore::GetInstance()->GetVolume(name);
    if (v == nullptr) {
      Fatal("Cannot find ignored volume: " + name + " in the actor " +
            fActorName);
    }
  }
}

void GateVBiasOptrActor::Configure() {
  if (!G4Threading::IsMultithreadedApplication())
    ConfigureForWorker();
}

void GateVBiasOptrActor::ConfigureForWorker() {
  auto *biasedVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  if (biasedVolume == nullptr) {
    Fatal("Cannot find biased volume: " + fAttachedToVolumeName + " in actor" +
          fActorName);
  }
  AttachAllLogicalDaughtersVolumes(biasedVolume);
}

void GateVBiasOptrActor::PreUserTrackingAction(const G4Track *track) {
  // WARNING this is needed in the MT mode (only),
  // otherwise, StartTracking is not called
  if (G4Threading::IsMultithreadedApplication()) {
    StartTracking(track);
  }
}

void GateVBiasOptrActor::AttachAllLogicalDaughtersVolumes(
    G4LogicalVolume *volume) {
  // Do not attach to ignored volumes
  const auto iter = std::find(fIgnoredVolumes.begin(), fIgnoredVolumes.end(),
                              volume->GetName());
  if (iter != fIgnoredVolumes.end())
    return;

  // Attach to the volume
  AttachTo(volume);

  // Propagate to daughters
  // FIXME: set an option to not propagate to daughters ?
  for (auto i = 0; i < volume->GetNoDaughters(); i++) {
    G4LogicalVolume *logicalDaughtersVolume =
        volume->GetDaughter(i)->GetLogicalVolume();
    AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
  }
}

void GateVBiasOptrActor::SteppingAction(G4Step *step) {
  if (step->GetTrack()->GetWeight() < fMinimalWeight) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
  }
}
