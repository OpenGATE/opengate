/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniqueVolumeIDManager.h"
#include "GateHelpers.h"

G4Mutex GetVolumeIDMutex = G4MUTEX_INITIALIZER;

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

  // However, without the mutex, it sef fault sometimes in MT mode.
  // Maybe due to some race condition around the shared_ptr. I don't know.
  // With the mutex, no seg fault.
  G4AutoLock mutex(&GetVolumeIDMutex);

  // https://geant4-forum.web.cern.ch/t/identification-of-unique-physical-volumes-with-ids/2568/3
  // ID
  auto name = touchable->GetVolume()->GetName();
  auto id = GateUniqueVolumeID::ComputeArrayID(touchable);
  // Search if this touchable has already been associated with a unique volume
  // ID
  if (fToVolumeID.count({name, id}) == 0) {
    // It does not exist, so we create it.
    auto uid = GateUniqueVolumeID::New(touchable);
    fToVolumeID[{name, id}] = uid;
  }
  return fToVolumeID.at({name, id});
}

std::vector<GateUniqueVolumeID::Pointer>
GateUniqueVolumeIDManager::GetAllVolumeIDs() const {
  std::vector<GateUniqueVolumeID::Pointer> l;
  for (const auto &x : fToVolumeID) {
    l.push_back(x.second);
  }
  return l; // copy
}
