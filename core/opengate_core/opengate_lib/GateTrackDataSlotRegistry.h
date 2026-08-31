/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTrackDataSlotRegistry_h
#define GateTrackDataSlotRegistry_h

#include <map>
#include <string>

struct GateTrackDataSlotInfo {
  int id{-1};
  std::string slot_name;
  std::string owner_kind;
  std::string owner_name;
  std::string value_type;
};

class GateTrackDataSlotRegistry {
public:
  static int RegisterSlot(const std::string &slot_name,
                          const std::string &owner_kind,
                          const std::string &owner_name,
                          const std::string &value_type);
  static const GateTrackDataSlotInfo *GetSlotInfo(int id);
  static const GateTrackDataSlotInfo *GetSlotInfo(const std::string &slot_name);
  static void Clear();

protected:
  static std::map<std::string, GateTrackDataSlotInfo> fRegisteredSlotsByName;
  static std::map<int, GateTrackDataSlotInfo *> fRegisteredSlotsByID;
  static int fNextSlotID;
};

#endif // GateTrackDataSlotRegistry_h
