/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <iostream>
#include "G4RunManager.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GamHitsProjectionActor.h"
#include "GamDictHelpers.h"
#include "GamHitsCollectionManager.h"
#include "GamImageHelpers.h"

GamHitsProjectionActor::GamHitsProjectionActor(py::dict &user_info)
        : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("BeginOfRunAction");
    fOutputFilename = DictStr(user_info, "output");
    fInputHitsCollectionNames = DictVecStr(user_info, "input_hits_collections");
    fImage = ImageType::New();
}

GamHitsProjectionActor::~GamHitsProjectionActor() {
}

// Called when the simulation start
void GamHitsProjectionActor::StartSimulationAction() {
    // Get input hits collection
    auto hcm = GamHitsCollectionManager::GetInstance();
    for (auto name: fInputHitsCollectionNames) {
        auto hc = hcm->GetHitsCollection(name);
        fInputHitsCollections.push_back(hc);
        CheckThatAttributeExists(hc, "PostPosition");
    }

    auto pvs = G4PhysicalVolumeStore::GetInstance();
    //fPreviousTranslation = pv->GetTranslation();
    std::string vol_name = "spect_crystal";
    G4ThreeVector translation;
    G4RotationMatrix rotation;
    bool first = true;
    while (vol_name != "world") {
        auto pv = pvs->GetVolume(vol_name); // FIXME parameter mother ?
        auto tr = pv->GetObjectTranslation();
        auto rot = pv->GetObjectRotation();
        if (first) {
            translation = tr;
            rotation.set(rot->rep3x3());
        } else {
            // crot = np.matmul(rot, crot)
            //            ctr = rot.dot(ctr) + tr
            rotation = (*rot) * rotation;
            translation = (*rot) * translation + tr;
        }

        vol_name = pv->GetMotherLogical()->GetName();
        first = false;
        DDD(vol_name);
    }

    fPreviousTranslation = translation;
    fPreviousRotation = rotation;
    DDD(fPreviousTranslation);
    DDD(fPreviousRotation);
}

void GamHitsProjectionActor::BeginOfRunAction(const G4Run *run) {
    DDD("");
    DDD("GamHitsProjectionActor::BeginOfRunAction");
    auto &l = fThreadLocalData.Get();
    if (run->GetRunID() == 0) {
        l.fIndex.resize(fInputHitsCollectionNames.size());
        l.fInputPos.resize(fInputHitsCollectionNames.size());
        for (size_t slice = 0; slice < fInputHitsCollections.size(); slice++) {
            l.fIndex[slice] = 0;
            auto att_pos = fInputHitsCollections[slice]->GetHitAttribute("PostPosition");
            l.fInputPos[slice] = &att_pos->Get3Values();
        }
    }

    DDD(fImage->GetOrigin());
    DDD(fImage->GetDirection());
    // FIXME update origin and rotation (phys volume may have changed !)
    /*
     vol = vol.g4_physical_volumes[0].GetName()
        translation, rotation = gam.get_transform_world_to_local(vol)
        t = gam.get_translation_from_rotation_with_center(Rotation.from_matrix(rotation), img_center)
        # compute the corresponding origin of the image
        origin = translation + img_center - t
        self.image.SetOrigin(origin)
        self.image.SetDirection(rotation)
     */
    /*
    DDD("GamHitsProjectionActor");
    auto origin = fImage->GetOrigin();
    DDD(origin);
    DDD(fImage->GetDirection());

    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto pv = pvs->GetVolume("spect_crystal"); // FIXME parameter mother ?
    // FIXME to world !!
    //auto t = pv->GetTranslation();
    auto t = pv->GetObjectTranslation();
    auto rot = pv->GetObjectRotation()->inverse(); // need inverse in the image
    DDD(t);
    for (auto i = 0; i < 3; i++)
        origin[i] = origin[i] - fPreviousTranslation[i] + t[i];
    DDD(origin);
    fImage->SetOrigin(origin);
    auto dir = fImage->GetDirection();
    DDD(rot);
    for (auto i = 0; i < 3; i++)
        for (auto j = 0; j < 3; j++)
            dir(i, j) = rot(i, j);
    fImage->SetDirection(dir);
    DDD(fImage->GetDirection());
     */
}

void GamHitsProjectionActor::EndOfEventAction(const G4Event *) {
    auto run = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
    for (size_t channel = 0; channel < fInputHitsCollections.size(); channel++) {
        auto slice = channel + run * fInputHitsCollections.size();
        //DD(slice);
        ProcessSlice(slice, channel);
    }
}

void GamHitsProjectionActor::ProcessSlice(size_t slice, size_t channel) {
    auto &l = fThreadLocalData.Get();
    auto &index = l.fIndex[channel];
    auto hc = fInputHitsCollections[channel];
    auto n = hc->GetSize() - index;

    // If no new hits, do nothing
    if (n <= 0) return;

    // FIXME store attribute somewhere
    const auto &pos = *l.fInputPos[channel];
    ImageType::PointType point;
    ImageType::IndexType pindex;
    for (size_t i = index; i < hc->GetSize(); i++) {
        // get position from input collection
        for (auto j = 0; j < 3; j++) point[j] = pos[i][j];
        //DDD(point);
        bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
        //DDD(pindex);
        //DDD(isInside);
        // force the slice according to the channel
        pindex[2] = slice;
        //DDD(pindex);
        if (isInside) {
            ImageAddValue<ImageType>(fImage, pindex, 1);
        } else {
            DDD(isInside);
            DDD(pindex);
            DDD(fImage->GetLargestPossibleRegion().GetSize());
        }

    }

    // update the hits index (thread local)
    index = hc->GetSize();
}

