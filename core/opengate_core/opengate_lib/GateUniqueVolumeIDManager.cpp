/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniqueVolumeIDManager.h"
#include "GateGeometryUtils.h"
#include "GateHelpers.h"
#include <shared_mutex>

G4Cache<GateUniqueVolumeIDManager::threadLocalT>
    GateUniqueVolumeIDManager::fThreadLocalData;
GateUniqueVolumeIDManager *GateUniqueVolumeIDManager::fInstance = nullptr;

GateUniqueVolumeIDManager *GateUniqueVolumeIDManager::GetInstance() {
  if (fInstance == nullptr) {
    fInstance = new GateUniqueVolumeIDManager();
  }
  return fInstance;
}

GateUniqueVolumeIDManager::GateUniqueVolumeIDManager() = default;

GateUniqueVolumeID::Pointer
GateUniqueVolumeIDManager::GetVolumeID(const G4VTouchable *touchable) {
  const auto name = touchable->GetVolume()->GetName();
  const auto id = GateUniqueVolumeID::ComputeArrayID(touchable);
  const auto key = std::make_pair(name, id);

  // Check thread-local cache
  auto &l = fThreadLocalData.Get();
  auto it = l.fToVolumeID.find(key);
  if (it != l.fToVolumeID.end()) {
    return it->second;
  }

  // Create a new GateUniqueVolumeID
  const auto uid = GateUniqueVolumeID::New(touchable);

  // Also generate the unique int id
  const auto *lv = touchable->GetVolume()->GetLogicalVolume();
  uid->fNumericID =
      GetNumericID(lv, uid->fID); // FIXME should it be lazy, on demand ?
  l.fToVolumeID[key] = uid;

  return uid;
}

std::vector<GateUniqueVolumeID::Pointer>
GateUniqueVolumeIDManager::GetAllVolumeIDs() const {
  auto &l = fThreadLocalData.Get();
  std::vector<GateUniqueVolumeID::Pointer> list;
  list.reserve(l.fToVolumeID.size());
  for (const auto &x : l.fToVolumeID) {
    list.push_back(x.second);
  }
  return list; // copy
}

int GateUniqueVolumeIDManager::GetNumericID(const G4LogicalVolume *lv,
                                            const std::string &id) {
  auto &l = fThreadLocalData.Get();
  auto it = l.fLVtoNumericIds.find(lv);
  if (it != l.fLVtoNumericIds.end()) {
    auto idIt = it->second.find(id);
    if (idIt != it->second.end()) {
      return idIt->second;
    }
  }

  // Not found, need to initialize all IDs for this LV
  InitializeNumericIDsForLV(lv);

  it = l.fLVtoNumericIds.find(lv);
  if (it != l.fLVtoNumericIds.end()) {
    return it->second.at(id);
  }

  // Should never reach here
  Fatal("Failed to initialize numeric ID");
  return -1;
}

void GateUniqueVolumeIDManager::InitializeNumericIDsForLV(
    const G4LogicalVolume *lv) {
  auto &l = fThreadLocalData.Get();

  // Collect all touchables for this LV
  const auto touchables = FindAllTouchables(lv->GetName());

  std::vector<std::string> stringIDs;
  stringIDs.reserve(touchables.size());
  for (const auto &touchable : touchables) {
    stringIDs.push_back(GateUniqueVolumeID::ComputeStringID(touchable.get()));
  }

  // Sort for deterministic ordering
  std::sort(stringIDs.begin(), stringIDs.end());

  // Assign sequential IDs
  std::map<std::string, int> sIDRegistry;
  int nextID = 1;
  for (const auto &stringID : stringIDs) {
    if (sIDRegistry.find(stringID) == sIDRegistry.end()) {
      sIDRegistry[stringID] = nextID++;
    }
  }

  l.fLVtoNumericIds[lv] = std::move(sIDRegistry);
}

void GateUniqueVolumeIDManager::Clear() {
  auto &l = fThreadLocalData.Get();
  l.fToVolumeID.clear();
  l.fLVtoNumericIds.clear();
}
