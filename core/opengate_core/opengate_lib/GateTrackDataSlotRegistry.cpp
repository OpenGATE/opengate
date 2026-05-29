/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTrackDataSlotRegistry.h"
#include "GateHelpers.h"

std::map<std::string, GateTrackDataSlotInfo>
    GateTrackDataSlotRegistry::fRegisteredSlotsByName;
std::map<int, GateTrackDataSlotInfo *>
    GateTrackDataSlotRegistry::fRegisteredSlotsByID;
int GateTrackDataSlotRegistry::fNextSlotID = 0;

int GateTrackDataSlotRegistry::RegisterSlot(const std::string &slot_name,
                                            const std::string &owner_kind,
                                            const std::string &owner_name,
                                            const std::string &value_type) {
  const auto existing = fRegisteredSlotsByName.find(slot_name);
  if (existing != fRegisteredSlotsByName.end()) {
    const auto &info = existing->second;
    if (info.owner_kind != owner_kind || info.owner_name != owner_name ||
        info.value_type != value_type) {
      Fatal("Track-data slot '" + slot_name +
            "' is already registered with different metadata.");
    }
    return info.id;
  }

  GateTrackDataSlotInfo info;
  info.id = fNextSlotID++;
  info.slot_name = slot_name;
  info.owner_kind = owner_kind;
  info.owner_name = owner_name;
  info.value_type = value_type;
  auto [it, inserted] = fRegisteredSlotsByName.emplace(slot_name, info);
  fRegisteredSlotsByID[it->second.id] = &it->second;
  return it->second.id;
}

const GateTrackDataSlotInfo *GateTrackDataSlotRegistry::GetSlotInfo(int id) {
  const auto it = fRegisteredSlotsByID.find(id);
  if (it == fRegisteredSlotsByID.end())
    return nullptr;
  return it->second;
}

const GateTrackDataSlotInfo *
GateTrackDataSlotRegistry::GetSlotInfo(const std::string &slot_name) {
  const auto it = fRegisteredSlotsByName.find(slot_name);
  if (it == fRegisteredSlotsByName.end())
    return nullptr;
  return &it->second;
}

void GateTrackDataSlotRegistry::Clear() {
  fRegisteredSlotsByID.clear();
  fRegisteredSlotsByName.clear();
  fNextSlotID = 0;
}
