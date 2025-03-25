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
  fIsActive = true;
}

void GateVBiasOptrActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fIgnoredVolumes = DictGetVecStr(user_info, "ignored_volumes");
  DDDV(fIgnoredVolumes);

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
  if (fAttachedToVolumeName.empty()) {
    fIsActive = false;
    return;
  }
  if (!G4Threading::IsMultithreadedApplication()) {
    auto *biasedVolume =
        G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
    if (biasedVolume == nullptr) {
      Fatal("Cannot find biased volume: " + fAttachedToVolumeName +
            " in actor" + fActorName);
    }
    AttachAllLogicalDaughtersVolumes(biasedVolume);
  }
}

void GateVBiasOptrActor::ConfigureForWorker() {
  if (fAttachedToVolumeName.empty()) {
    fIsActive = false;
    return;
  }
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
  // FIXME: set an option to not propagate to daughters ?

  // Do not attach to ignored volumes
  const auto iter = std::find(fIgnoredVolumes.begin(), fIgnoredVolumes.end(),
                              volume->GetName());
  if (iter != fIgnoredVolumes.end())
    return;
  DDD(volume->GetName());

  AttachTo(volume);
  for (auto i = 0; i < volume->GetNoDaughters(); i++) {
    G4LogicalVolume *logicalDaughtersVolume =
        volume->GetDaughter(i)->GetLogicalVolume();
    AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
  }
}
