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
    Global singleton class that manage a correspondence between touchable pointer and unique volume ID.


 */

class GamUniqueVolumeIDManager {
public:

    static GamUniqueVolumeIDManager *GetInstance();

    GamUniqueVolumeID::Pointer GetVolumeID(const G4VTouchable *touchable);

    const std::map<std::string, GamUniqueVolumeID::Pointer> &GetAllVolumeIDs() const;

protected:
    GamUniqueVolumeIDManager();

    static GamUniqueVolumeIDManager *fInstance;

    std::map<const G4VTouchable *, GamUniqueVolumeID::Pointer> fMapOfTouchableToVolumeID;
    std::map<std::string, GamUniqueVolumeID::Pointer> fMapOfIDToTouchable;

};


#endif // GamUniqueVolumeIDManager_h
