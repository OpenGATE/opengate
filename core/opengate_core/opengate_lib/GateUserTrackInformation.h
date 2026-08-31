/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUserTrackInformation_h
#define GateUserTrackInformation_h

#include "GateHelpers.h"
#include "GateTrackData.h"
#include <G4VUserTrackInformation.hh>
#include <map>
#include <memory>
#include <sstream>
#include <tuple>

class GateUserTrackInformation : public G4VUserTrackInformation {
public:
  GateUserTrackInformation() = default;
  ~GateUserTrackInformation() override = default;

  GateVTrackData *GetTrackData(int slot_id) const {
    const auto it = fMapOfTrackInformation.find(slot_id);
    if (it == fMapOfTrackInformation.end())
      return nullptr;
    return it->second.get();
  }

  bool HasTrackData(int slot_id) const {
    return fMapOfTrackInformation.find(slot_id) != fMapOfTrackInformation.end();
  }

  void SetTrackData(int slot_id, std::unique_ptr<GateVTrackData> track_data) {
    fMapOfTrackInformation[slot_id] = std::move(track_data);
  }

  void RemoveTrackData(int slot_id) { fMapOfTrackInformation.erase(slot_id); }

  template <typename TrackDataType>
  TrackDataType *GetTrackData(int slot_id) const {
    auto *track_data = GetTrackData(slot_id);
    if (track_data == nullptr)
      return nullptr;
    auto *typed_track_data = dynamic_cast<TrackDataType *>(track_data);
    if (typed_track_data == nullptr) {
      std::ostringstream oss;
      oss << "Track data slot " << slot_id << " has an unexpected type.";
      Fatal(oss.str());
    }
    return typed_track_data;
  }

  template <typename TrackDataType>
  TrackDataType *GetOrCreateTrackData(int slot_id) {
    auto *track_data = GetTrackData<TrackDataType>(slot_id);
    if (track_data != nullptr)
      return track_data;
    auto owned_track_data = std::make_unique<TrackDataType>();
    auto *raw_ptr = owned_track_data.get();
    SetTrackData(slot_id, std::move(owned_track_data));
    return raw_ptr;
  }

  static int64_t CodeShowerID(const int eventID, const int trackID,
                              const int splitID) {
    // New bit allocation:
    // eventID:       32 bits (bits 32-63) -> supports up to ~4.2 billion events
    // parentTrackID: 16 bits (bits 16-31) -> supports up to 65,536 tracks
    // splitID:      16 bits (bits 0-15)   -> supports up to 65,536 splits

    return ((int64_t)eventID << 32) | ((int64_t)(trackID & 0xFFFF) << 16) |
           (splitID & 0xFFFF);
  }

  static std::tuple<int, int, int> DecodeShowerID(const int64_t showerID) {
    return {
        (int)(showerID >> 32),            // eventID
        (int)((showerID >> 16) & 0xFFFF), // trackID
        (int)(showerID & 0xFFFF)          // splitID
    };
  }

protected:
  std::map<int, std::unique_ptr<GateVTrackData>> fMapOfTrackInformation;
};

inline GateUserTrackInformation *
GetGateUserTrackInformation(const G4Track *track) {
  if (track == nullptr)
    return nullptr;
  auto *user_info = track->GetUserInformation();
  if (user_info == nullptr)
    return nullptr;
  auto *gate_user_info = dynamic_cast<GateUserTrackInformation *>(user_info);
  if (gate_user_info == nullptr) {
    Fatal("Track user information exists but is not a GateUserTrackInformation "
          "instance.");
  }
  return gate_user_info;
}

inline GateUserTrackInformation *
GetOrCreateGateUserTrackInformation(const G4Track *track) {
  if (track == nullptr)
    return nullptr;
  auto *gate_user_info = GetGateUserTrackInformation(track);
  if (gate_user_info != nullptr)
    return gate_user_info;
  gate_user_info = new GateUserTrackInformation();
  const_cast<G4Track *>(track)->SetUserInformation(gate_user_info);
  return gate_user_info;
}

#endif // GateUserTrackInformation_h
