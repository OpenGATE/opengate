/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamUniqueVolumeID.h"
#include "GamHelpers.h"
#include "G4VPhysicalVolume.hh"
#include "G4NavigationHistory.hh"
#include "G4RunManager.hh"


GamUniqueVolumeID::GamUniqueVolumeID() {
    fID = "undefined_Unique_Volume_ID";
}

GamUniqueVolumeID::Pointer GamUniqueVolumeID::New(const G4VTouchable *touchable) {
    if (touchable == nullptr)
        return std::make_shared<GamUniqueVolumeID>();
    return std::make_shared<GamUniqueVolumeID>(touchable);
}

GamUniqueVolumeID::GamUniqueVolumeID(const G4VTouchable *touchable) {
    // retrieve the tree of embedded volumes
    const auto *hist = touchable->GetHistory();
    for (auto i = 0; i <= (int) hist->GetDepth(); i++) {
        auto v = GamUniqueVolumeID::VolumeDepthID();
        v.fVolumeName = hist->GetVolume(i)->GetName();
        v.fCopyNb = hist->GetVolume(i)->GetCopyNo();
        v.fDepth = i;
        v.fTransform = hist->GetTransform(i); // copy
        v.fVolume = hist->GetVolume(i);
        fVolumeDepthID.push_back(v);
    }
    // compute the final ID (str)
    std::ostringstream oss;
    const auto &last = fVolumeDepthID.back();
    for (const auto &h: fVolumeDepthID) {
        if (&last == &h) oss << h.fCopyNb;
        else oss << h.fCopyNb << "_";
    }
    fID = oss.str();
}


std::ostream &operator<<(std::ostream &os,
                         const GamUniqueVolumeID::VolumeDepthID &v) {
    os << v.fDepth << " "
       << v.fVolumeName << " "
       << v.fCopyNb;
    return os;
}
//-----------------------------------------------------------------------------------

