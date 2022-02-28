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
#include "GamHelpersDict.h"
#include "GamHitsCollectionManager.h"
#include "GamHelpersImage.h"

GamHitsProjectionActor::GamHitsProjectionActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("BeginOfRunAction");
    fOutputFilename = DictStr(user_info, "output");
    //fVolumeName = DictStr(user_info, "mother");
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
        // The first here we need to initialize the index and inputpos
        l.fIndex.resize(fInputHitsCollectionNames.size());
        l.fInputPos.resize(fInputHitsCollectionNames.size());
        for (size_t slice = 0; slice < fInputHitsCollections.size(); slice++) {
            l.fIndex[slice] = 0;
            auto att_pos = fInputHitsCollections[slice]->GetHitAttribute("PostPosition");
            l.fInputPos[slice] = &att_pos->Get3Values();
        }
    }

    // Important ! The volume may have moved, so we re-attach each run
    AttachImageToVolume<ImageType>(fImage, fPhysicalVolumeName);
}

void GamHitsProjectionActor::EndOfEventAction(const G4Event *) {
    auto run = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
    for (size_t channel = 0; channel < fInputHitsCollections.size(); channel++) {
        auto slice = channel + run * fInputHitsCollections.size();
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
        bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
        // force the slice according to the channel
        pindex[2] = slice;
        if (isInside) {
            ImageAddValue<ImageType>(fImage, pindex, 1);
        } else {
            // Should never be here (?)
            /*
             DDD(isInside);
             DDD(pindex);
             DDD(fImage->GetLargestPossibleRegion().GetSize());
             */
        }

    }

    // update the hits index (thread local)
    index = hc->GetSize();
}

