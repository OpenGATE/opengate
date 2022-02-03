/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <iostream>
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
}

void GamHitsProjectionActor::BeginOfRunAction(const G4Run *run) {
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
}

void GamHitsProjectionActor::EndOfEventAction(const G4Event *) {
    for (size_t slice = 0; slice < fInputHitsCollections.size(); slice++)
        ProcessSlice(slice);

}

void GamHitsProjectionActor::ProcessSlice(size_t slice) {
    auto &l = fThreadLocalData.Get();
    auto &index = l.fIndex[slice];
    auto hc = fInputHitsCollections[slice];
    auto n = hc->GetSize() - index;

    // If no new hits, do nothing
    if (n <= 0) return;

    // FIXME store attribute somewhere
    auto &pos = *l.fInputPos[slice];
    ImageType::PointType point;
    ImageType::IndexType pindex;
    for (size_t i = index; i < hc->GetSize(); i++) {
        // get position from input collection
        for (auto j = 0; j < 3; j++) point[j] = pos[i][j];
        bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
        // force the slice according to the channel
        pindex[2] = slice;
        if (isInside)
            ImageAddValue<ImageType>(fImage, pindex, 1);

    }

    // update the hits index (thread local)
    index = hc->GetSize();
}

