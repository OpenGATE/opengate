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
    // This function is potentially called a large number of time (every hit)
    // It worth it to make it faster if possible (unsure how).

    // https://geant4-forum.web.cern.ch/t/identification-of-unique-physical-volumes-with-ids/2568/3
    // ID
    auto id = GamUniqueVolumeID::ComputeArrayID(touchable);
    // Search if this touchable has already been associated with a unique volume ID
    if (fArrayToVolumeID.count(id) == 0) {
        // It does not exist, so we create it.
        auto uid = GamUniqueVolumeID::New(touchable);
        fNameToVolumeID[uid->fID] = uid;
        fArrayToVolumeID[id] = uid;
    }
    return fArrayToVolumeID[id];
}

std::vector<GamUniqueVolumeID::Pointer> GamUniqueVolumeIDManager::GetAllVolumeIDs() const {
    std::vector<GamUniqueVolumeID::Pointer> l;
    for (const auto &x: fNameToVolumeID) {
        l.push_back(x.second);
    }
    return l; // copy
}
