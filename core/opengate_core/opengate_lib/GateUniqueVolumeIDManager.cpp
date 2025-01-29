/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniqueVolumeIDManager.h"
#include "GateHelpers.h"
#include <shared_mutex>

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

  // Gain read access before checking if the touchable has already
  // been associated with a unique volume ID.
  std::shared_lock<std::shared_mutex> readLock(GetVolumeIDMutex);
  auto it = fToVolumeID.find({name, id});
  if (it != fToVolumeID.end()) {
    return it->second;
  } else {
    // The volume ID does not exist yet, so we will create it.
    readLock.unlock();
    const auto uid = GateUniqueVolumeID::New(touchable);
    // Before modifying the map, we must obtain exclusive write access.
    std::unique_lock<std::shared_mutex> writeLock(GetVolumeIDMutex);
    // There is a chance that another thread has already created the volume ID
    // in the time interval between unlocking the read lock and locking the
    // write lock, so we have to check again if the volume ID exists already.
    it = fToVolumeID.find({name, id});
    if (it != fToVolumeID.end()) {
      return it->second;
    } else {
      // Add the new ID to the map and return it.
      fToVolumeID[{name, id}] = uid;
      return uid;
    }
  }
}

std::vector<GateUniqueVolumeID::Pointer>
GateUniqueVolumeIDManager::GetAllVolumeIDs() const {
  std::vector<GateUniqueVolumeID::Pointer> l;
  for (const auto &x : fToVolumeID) {
    l.push_back(x.second);
  }
  return l; // copy
}
