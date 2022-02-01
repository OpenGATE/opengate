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
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictStr(user_info, "output");
    fInputHitsCollectionName = DictStr(user_info, "input_hits_collections");
    fInputHitsCollection = nullptr;
    fImage = ImageType::New();
}

GamHitsProjectionActor::~GamHitsProjectionActor() {
}

// Called when the simulation start
void GamHitsProjectionActor::StartSimulationAction() {
    // Get input hits collection
    auto hcm = GamHitsCollectionManager::GetInstance();
    fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);;
    CheckThatAttributeExists(fInputHitsCollection, "PostPosition");
}

void GamHitsProjectionActor::BeginOfRunAction(const G4Run *run) {
    auto &l = fThreadLocalData.Get();
    if (run->GetRunID() == 0) {
        l.fInputEdep = &fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit")->GetDValues();
    }
    l.fIndex = 0;
}

void GamHitsProjectionActor::BeginOfEventAction(const G4Event *) {
    // nothing
}

void GamHitsProjectionActor::EndOfEventAction(const G4Event *) {
    auto &index = fThreadLocalData.Get().fIndex;
    auto n = fInputHitsCollection->GetSize() - index;
    // If no new hits, do nothing
    if (n <= 0) return;

    // FIXME fill image here
    auto att_pos = fInputHitsCollection->GetHitAttribute("PostPosition");
    auto &pos = att_pos->Get3Values();
    ImageType::PointType point;
    ImageType::IndexType pindex;
    for (size_t i = index; i < fInputHitsCollection->GetSize(); i++) {
        //DDD(i);
        // get position from input collection
        for (auto j = 0; j < 3; j++) point[j] = pos[i][j];
        //DDD(pos[i]);
        //DDD(point);
        bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
        //DDD(pindex);
        if (isInside) {
            ImageAddValue<ImageType>(fImage, pindex, 1);
        }
    }


    // update the hits index (thread local)
    index = fInputHitsCollection->GetSize();
}

// Called every time a Run ends
void GamHitsProjectionActor::EndOfRunAction(const G4Run *) {
}

// Called every time a Run ends
void GamHitsProjectionActor::EndOfSimulationWorkerAction(const G4Run *) {
}

// Called when the simulation end
void GamHitsProjectionActor::EndSimulationAction() {
}

