/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniqueVolumeIDManager.h"
#include "GateHelpers.h"
#include <shared_mutex>

// This mutex protects access to the fToVolumeID map
std::shared_mutex GetVolumeIDMutex;

GateUniqueVolumeIDManager *GateUniqueVolumeIDManager::fInstance = nullptr;

GateUniqueVolumeIDManager *GateUniqueVolumeIDManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateUniqueVolumeIDManager();
  return fInstance;
}

GateUniqueVolumeIDManager::GateUniqueVolumeIDManager() = default;

GateUniqueVolumeID::Pointer
GateUniqueVolumeIDManager::GetVolumeID(const G4VTouchable *touchable) {
  // Since this function can be called from different threads,
  // the map fToVolumeID must be protected against concurrent modifications.
  // Concurrent reads of fToVolumeID are allowed, however.

  // Since this function is potentially called a large number of times (every
  // hit), locks need to be in place as briefly as possible.

  // https://geant4-forum.web.cern.ch/t/identification-of-unique-physical-volumes-with-ids/2568/3
  const auto name = touchable->GetVolume()->GetName();
  const auto id = GateUniqueVolumeID::ComputeArrayID(touchable);

  // Gain read access to check if the ID already exists
  std::shared_lock<std::shared_mutex> readLock(GetVolumeIDMutex);
  auto it = fToVolumeID.find({name, id});
  if (it != fToVolumeID.end()) {
    return it->second;
  } else {
    // The volume ID does not exist yet, so we will create it.
    readLock.unlock();

    std::unique_lock<std::shared_mutex> writeLock(GetVolumeIDMutex);

    // Check again in case another thread created it in the meantime
    it = fToVolumeID.find({name, id});
    if (it != fToVolumeID.end()) {
      return it->second;
    } else {
      // Create the new GateUniqueVolumeID. It will generate its own IDs
      // internally.
      const auto uid = GateUniqueVolumeID::New(touchable);

      // Add the new ID to the map and return it.
      fToVolumeID[{name, id}] = uid;
      return uid;
    }
  }
}

std::vector<GateUniqueVolumeID::Pointer>
GateUniqueVolumeIDManager::GetAllVolumeIDs() const {
  std::vector<GateUniqueVolumeID::Pointer> l;
  l.reserve(fToVolumeID.size());
  for (const auto &x : fToVolumeID) {
    l.push_back(x.second);
  }
  return l; // copy
}
