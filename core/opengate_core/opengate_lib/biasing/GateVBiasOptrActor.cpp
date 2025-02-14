/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVBiasOptrActor.h"
#include "../GateHelpers.h"
#include "G4LogicalVolumeStore.hh"
#include "G4RunManager.hh"

GateVBiasOptrActor::GateVBiasOptrActor(const std::string &name,
                                       py::dict &user_info, const bool MT_ready)
    : G4VBiasingOperator(name), GateVActor(user_info, MT_ready) {
  // It seems that it is needed in MT (see PreUserTrackingAction)
  fActions.insert("PreUserTrackingAction");
}

void GateVBiasOptrActor::Configure() {
  if (!G4Threading::IsMultithreadedApplication()) {
    auto *biasedVolume =
        G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
    AttachAllLogicalDaughtersVolumes(biasedVolume);
  }
}

void GateVBiasOptrActor::ConfigureForWorker() {
  auto *biasedVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  AttachAllLogicalDaughtersVolumes(biasedVolume);
}

void GateVBiasOptrActor::PreUserTrackingAction(const G4Track *track) {
  // This is needed in the MT mode (only), otherwise, StartTracking is not
  // called
  if (G4Threading::IsMultithreadedApplication()) {
    StartTracking(track);
  }
}

void GateVBiasOptrActor::AttachAllLogicalDaughtersVolumes(
    G4LogicalVolume *volume) {
  // FIXME: set an option to no propagate to daughters
  AttachTo(volume);
  for (auto i = 0; i < volume->GetNoDaughters(); i++) {
    G4LogicalVolume *logicalDaughtersVolume =
        volume->GetDaughter(i)->GetLogicalVolume();
    AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
  }
}
