/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniqueVolumeIDManager.h"
#include "GateHelpers.h"

GateUniqueVolumeIDManager *GateUniqueVolumeIDManager::fInstance = nullptr;

GateUniqueVolumeIDManager *GateUniqueVolumeIDManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateUniqueVolumeIDManager();
  return fInstance;
}

GateUniqueVolumeIDManager::GateUniqueVolumeIDManager() = default;

GateUniqueVolumeID::Pointer
GateUniqueVolumeIDManager::GetVolumeID(const G4VTouchable *touchable) {
  // This function is potentially called a large number of time (every hit)
  // It worth it to make it faster if possible (unsure how).

  // https://geant4-forum.web.cern.ch/t/identification-of-unique-physical-volumes-with-ids/2568/3
  // ID
  auto id = GateUniqueVolumeID::ComputeArrayID(touchable);
  // Search if this touchable has already been associated with a unique volume
  // ID
  if (fArrayToVolumeID.count(id) == 0) {
    // It does not exist, so we create it.
    auto uid = GateUniqueVolumeID::New(touchable);
    fNameToVolumeID[uid->fID] = uid;
    fArrayToVolumeID[id] = uid;
  }
  return fArrayToVolumeID[id];
}

std::vector<GateUniqueVolumeID::Pointer>
GateUniqueVolumeIDManager::GetAllVolumeIDs() const {
  std::vector<GateUniqueVolumeID::Pointer> l;
  for (const auto &x : fNameToVolumeID) {
    l.push_back(x.second);
  }
  return l; // copy
}
