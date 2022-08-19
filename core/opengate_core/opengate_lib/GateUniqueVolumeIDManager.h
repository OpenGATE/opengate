/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUniqueVolumeIDManager_h
#define GateUniqueVolumeIDManager_h

#include "GateUniqueVolumeID.h"
#include "G4VTouchable.hh"

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

    // Index of ID array to VolumeID to speed up test
    // This map is created on the fly in GetVolumeID
    std::map<GateUniqueVolumeID::IDArrayType, GateUniqueVolumeID::Pointer> fArrayToVolumeID;

    // Convenient helpers map from name to VolumeID
    std::map<std::string, GateUniqueVolumeID::Pointer> fNameToVolumeID;

};

#endif // GateUniqueVolumeIDManager_h
