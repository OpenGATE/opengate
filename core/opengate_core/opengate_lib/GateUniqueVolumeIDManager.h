/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUniqueVolumeIDManager_h
#define GateUniqueVolumeIDManager_h

#include "G4VTouchable.hh"
#include "GateUniqueVolumeID.h"
#include <map>
#include <string>
#include <utility>
#include <vector>

/*
    Global singleton class that manage a correspondence between touchable
    pointer and unique volume ID.
 */

class GateUniqueVolumeIDManager {
public:
  // No constructor: get or create singleton
  static GateUniqueVolumeIDManager *GetInstance();

  // Get or create a VolumeID on demand, from a touchable
  GateUniqueVolumeID::Pointer GetVolumeID(const G4VTouchable *touchable);

  std::vector<GateUniqueVolumeID::Pointer> GetAllVolumeIDs() const;

  static void Clear();

protected:
  GateUniqueVolumeIDManager();
  static GateUniqueVolumeIDManager *fInstance;

  static void InitializeNumericIDsForLV(const G4LogicalVolume *lv);
  static int GetNumericID(const G4LogicalVolume *lv, const std::string &id);

  // Thread-local map: this duplicates the memory and the computation of the UiD
  // to all threads, but this avoids mutex and complex race conditions.
  struct threadLocalT {
    std::map<std::pair<std::string, GateUniqueVolumeID::IDArrayType>,
             GateUniqueVolumeID::Pointer>
        fToVolumeID;
    std::map<const G4LogicalVolume *, std::map<std::string, int>>
        fLVtoNumericIds;
  };
  static G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateUniqueVolumeIDManager_h
