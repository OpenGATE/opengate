/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <array>
#include <utility>

#include "GamUniqueVolumeID.h"
#include "GamHelpers.h"
#include "G4VPhysicalVolume.hh"
#include "G4NavigationHistory.hh"
#include "G4RunManager.hh"


GamUniqueVolumeID::GamUniqueVolumeID() {
    fID = "undefined";
    NbCall = 0;
}

GamUniqueVolumeID::~GamUniqueVolumeID() {
}


GamUniqueVolumeID::Pointer GamUniqueVolumeID::New(const G4VTouchable *touchable) {
    if (touchable == nullptr)
        return std::make_shared<GamUniqueVolumeID>();
    return std::make_shared<GamUniqueVolumeID>(touchable);
}

GamUniqueVolumeID::IDArrayType
GamUniqueVolumeID::ComputeArrayID(const G4VTouchable *touchable) {
    /*
       WARNING. For an unknown (but probably good) reason,
       looping on the touchable->GetHistory() or looping with touchable->Get(depth)
       is not equivalent for parameterised volume.
       I choose to keep the latter as it leads to similar results
       between repeated or parametrised volumes.
     */
    const auto *hist = touchable->GetHistory();
//    DDD(touchable->GetCopyNumber(0));
    GamUniqueVolumeID::IDArrayType a{};
    a.fill(-1);
    /*for (auto i = 0; i <= (int) hist->GetDepth(); i++) {
        DDD(i);
        DDD(hist->GetVolume(i)->GetName());
        DDD(hist->GetVolume(i)->GetInstanceID());
        DDD(hist->GetVolume(i)->IsParameterised());
        DDD(hist->GetVolume(i)->IsRegularStructure());
        DDD(hist->GetVolume(i)->IsMany());
        DDD(hist->GetVolume(i)->IsReplicated());
        DDD(hist->GetVolume(i)->GetTranslation());
        auto n = hist->GetVolume(i)->GetCopyNo();
        DDD(hist->GetVolume(i)->GetCopyNo());
        a[i] = n;
    }
    DDD(ArrayIDToStr(a));
    DDD("--- version 2   --- ");
     */

    // Version 2
    for (auto i = 0; i <= (int) hist->GetDepth(); i++) {
        //DDD(i);
        a[i] = touchable->GetCopyNumber(hist->GetDepth() - i);
    }
    //DDD(ArrayIDToStr(a));
    //DDD("END");

    return a;
}


std::string GamUniqueVolumeID::ArrayIDToStr(IDArrayType id) {
    std::ostringstream oss;
    size_t i = 0;
    while (i < id.size() and id[i] != -1) {
        oss << id[i] << "_";
        i++;
    }
    auto s = oss.str();
    s.pop_back();
    return s;
}


GamUniqueVolumeID::GamUniqueVolumeID(const G4VTouchable *touchable) : GamUniqueVolumeID() {
    // retrieve the tree of embedded volumes
    // See ComputeArrayID warning for explanation.
    const auto *hist = touchable->GetHistory();
    /*for (auto i = 0; i <= (int) hist->GetDepth(); i++) {
        auto v = GamUniqueVolumeID::VolumeDepthID();
        v.fVolumeName = hist->GetVolume(i)->GetName();
        v.fCopyNb = hist->GetVolume(i)->GetCopyNo();
        v.fDepth = i;
        v.fTransform = hist->GetTransform(i); // copy the transform
        v.fVolume = hist->GetVolume(i);
        fVolumeDepthID.push_back(v);
    }*/

    // V2

    for (auto i = 0; i <= (int) hist->GetDepth(); i++) {
        //DDD(i);
        int index = (int) hist->GetDepth() - i;
        auto v = GamUniqueVolumeID::VolumeDepthID();
        v.fVolumeName = touchable->GetVolume(index)->GetName();
        v.fCopyNb = touchable->GetCopyNumber(index);
        v.fDepth = index;
        v.fTranslation = touchable->GetTranslation(index); // copy the transform
        v.fRotation = touchable->GetRotation(index); // copy the transform
        v.fVolume = touchable->GetVolume(index);
        fVolumeDepthID.push_back(v);
    }

    fArrayID = ComputeArrayID(touchable);
    fID = ArrayIDToStr(fArrayID);
}


std::ostream &operator<<(std::ostream &os,
                         const GamUniqueVolumeID::VolumeDepthID &v) {
    os << v.fDepth << " "
       << v.fVolumeName << " "
       << v.fCopyNb;
    return os;
}

const std::vector<GamUniqueVolumeID::VolumeDepthID> &GamUniqueVolumeID::GetVolumeDepthID() const {
    return fVolumeDepthID;
}
