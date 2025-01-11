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
#include <string>
#include <utility>

/*
    Global singleton class that manage a correspondence between touchable
    pointer and unique volume ID.
 */

class GateUniqueVolumeIDManager {
public:
  static GateUniqueVolumeIDManager *GetInstance();

  GateUniqueVolumeID::Pointer GetVolumeID(const G4VTouchable *touchable);

  std::vector<GateUniqueVolumeID::Pointer> GetAllVolumeIDs() const;

protected:
  GateUniqueVolumeIDManager();

  static GateUniqueVolumeIDManager *fInstance;

  // Index of name + ID array to VolumeID
  // This map is created on the fly in GetVolumeID
  std::map<std::pair<std::string, GateUniqueVolumeID::IDArrayType>,
           GateUniqueVolumeID::Pointer>
      fToVolumeID;
};

#endif // GateUniqueVolumeIDManager_h
