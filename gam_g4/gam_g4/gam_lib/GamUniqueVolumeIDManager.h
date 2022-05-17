/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamUniqueVolumeIDManager_h
#define GamUniqueVolumeIDManager_h

#include "GamUniqueVolumeID.h"
#include "G4VTouchable.hh"

/*
    Global singleton class that manage a correspondence between touchable
    pointer and unique volume ID.
 */

class GamUniqueVolumeIDManager {
public:

    static GamUniqueVolumeIDManager *GetInstance();

    GamUniqueVolumeID::Pointer GetVolumeID(const G4VTouchable *touchable);

    std::vector<GamUniqueVolumeID::Pointer> GetAllVolumeIDs() const;

protected:
    GamUniqueVolumeIDManager();

    static GamUniqueVolumeIDManager *fInstance;

    // Index of ID array to VolumeID to speed up test
    // This map is created on the fly in GetVolumeID
    std::map<GamUniqueVolumeID::IDArrayType, GamUniqueVolumeID::Pointer> fArrayToVolumeID;

    // Convenient helpers map from name to VolumeID
    std::map<std::string, GamUniqueVolumeID::Pointer> fNameToVolumeID;

};

#endif // GamUniqueVolumeIDManager_h
