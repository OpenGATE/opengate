/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVBiasOptrActor.h"
#include "G4BiasingProcessInterface.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"

GateVBiasOptrActor::GateVBiasOptrActor(std::string name, py::dict &user_info,
                                       bool MT_ready)
    : G4VBiasingOperator(name), GateVActor(user_info, MT_ready) {}

void GateVBiasOptrActor::Configure() {
  std::cout << "Configure" << std::endl;
  DDD(fAttachedToVolumeName);
  auto *biasedVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fAttachedToVolumeName);
  AttachAllLogicalDaughtersVolumes(biasedVolume);
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
  // std::cout << "AttachAllLogicalDaughtersVolumes" << std::endl;
  DDD(volume->GetName());
  AttachTo(volume);
  // FIXME user option
  G4int nbOfDaughters = volume->GetNoDaughters();
  if (nbOfDaughters > 0) {
    for (int i = 0; i < nbOfDaughters; i++) {
      G4LogicalVolume *logicalDaughtersVolume =
          volume->GetDaughter(i)->GetLogicalVolume();
      AttachAllLogicalDaughtersVolumes(logicalDaughtersVolume);
    }
  }
}
