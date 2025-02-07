/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVBiasOptrActor.h"
#include "../GateHelpers.h"
#include "G4BiasingProcessInterface.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"

GateVBiasOptrActor::GateVBiasOptrActor(const std::string &name,
                                       py::dict &user_info, const bool MT_ready)
    : G4VBiasingOperator(name), GateVActor(user_info, MT_ready) {}

void GateVBiasOptrActor::Configure() {
  std::cout << "Configure" << std::endl;
  if (!G4Threading::IsMultithreadedApplication()) {
    DDD(fAttachedToVolumeName);
    auto *biasedVolume =
        G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
    AttachAllLogicalDaughtersVolumes(biasedVolume);
  }
}

void GateVBiasOptrActor::ConfigureForWorker() {
  std::cout << "ConfigureForWorker" << std::endl;
  DDD(fAttachedToVolumeName);
  auto *biasedVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  AttachAllLogicalDaughtersVolumes(biasedVolume);
}

void GateVBiasOptrActor::AttachAllLogicalDaughtersVolumes(
    G4LogicalVolume *volume) {
  DDD(volume->GetName());
  AttachTo(volume);
  // FIXME user option
  for (auto i = 0; i < volume->GetNoDaughters(); i++) {
    G4LogicalVolume *logicalDaughtersVolume =
        volume->GetDaughter(i)->GetLogicalVolume();
    AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
  }
}
