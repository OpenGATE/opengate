/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVActor.h"
#include <G4VUserTrackInformation.hh>

class GateUserTrackInformation : public G4VUserTrackInformation {
public:
  GateUserTrackInformation() = default;
  ~GateUserTrackInformation() override = default;

  void SetGateTrackInformation(GateVActor *myActor, int64_t info) {
    fMapOfTrackInformation[myActor] = info;
  }

  int64_t GetGateTrackInformation(GateVActor *myActor) const {
    return fMapOfTrackInformation.at(myActor);
  }

  int64_t GetFirstValue() const {
    if (!fMapOfTrackInformation.empty()) {
      // The first element of a std::map is the one with the "smallest" key.
      // In this case, it's deterministic based on actor pointer addresses.
      return fMapOfTrackInformation.begin()->second;
    }
    return -1;
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

  std::map<GateVActor *, int64_t> fMapOfTrackInformation;
};