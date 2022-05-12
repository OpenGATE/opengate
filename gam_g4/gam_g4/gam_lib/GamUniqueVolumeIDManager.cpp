/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamUniqueVolumeIDManager.h"
#include "GamHelpers.h"

GamUniqueVolumeIDManager *GamUniqueVolumeIDManager::fInstance = nullptr;

GamUniqueVolumeIDManager *GamUniqueVolumeIDManager::GetInstance() {
    if (fInstance == nullptr) fInstance = new GamUniqueVolumeIDManager();
    return fInstance;
}

GamUniqueVolumeIDManager::GamUniqueVolumeIDManager() = default;

GamUniqueVolumeID::Pointer GamUniqueVolumeIDManager::GetVolumeID(const G4VTouchable *touchable) {
    // Search if this touchable has already been associated with a unique volume ID
    if (fMapOfTouchableToVolumeID.count(touchable) == 0) {
        // It does not exist, so we create it.
        auto uid = GamUniqueVolumeID::New(touchable);
        /* Warning : sometime several touchable will be associated with
         the same UniqueVolumeID. It cannot be known in advance, so we create
         again the same UVID. At the end, the final map
         fMapOfIDToTouchable will contain all created UVID.
         */
        fMapOfIDToTouchable[uid->fID] = uid;
        fMapOfTouchableToVolumeID[touchable] = uid;

    }
    // FIXME maybe this map is slow ?
    return fMapOfTouchableToVolumeID[touchable];
}

const std::map<std::string, GamUniqueVolumeID::Pointer> &GamUniqueVolumeIDManager::GetAllVolumeIDs() const {
    return fMapOfIDToTouchable;
}
