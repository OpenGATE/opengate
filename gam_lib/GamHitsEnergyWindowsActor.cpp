/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <iostream>
#include "GamHitsEnergyWindowsActor.h"
#include "GamDictHelpers.h"
#include "GamHitsCollectionManager.h"

GamHitsEnergyWindowsActor::GamHitsEnergyWindowsActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictStr(user_info, "output");
    fInputHitsCollectionName = DictStr(user_info, "input_hits_collection");

    auto dv = DictVecDict(user_info, "channels");
    DDD(dv.size());
    for (auto d: dv) {
        DDD(DictStr(d, "name"));
        DDD(DictFloat(d, "min"));
        DDD(DictFloat(d, "max"));
        fChannelNames.push_back(DictStr(d, "name"));
        fChannelMin.push_back(DictFloat(d, "min"));
        fChannelMax.push_back(DictFloat(d, "max"));
    }
    fInputHitsCollection = nullptr;
}

GamHitsEnergyWindowsActor::~GamHitsEnergyWindowsActor() {
}

// Called when the simulation start
void GamHitsEnergyWindowsActor::StartSimulationAction() {
    DDD("StartSimulationAction");
    // list of attributes
    std::vector<std::string> att;
    att.push_back("TotalEnergyDeposit");
    att.push_back("PostPosition"); // FIXME --> note really, copy all others
    // Create the output hits collections
    auto hcm = GamHitsCollectionManager::GetInstance();
    for (auto name: fChannelNames) {
        DDD(name);
        auto hc = hcm->NewHitsCollection(name);
        hc->SetFilename(fOutputFilename);
        hc->InitializeHitAttributes(att);
        hc->InitializeRootTupleForMaster();
        DDD(fOutputFilename);
        fChannelHitsCollections.push_back(hc);
    }

    DDD("end StartSimulationAction");
}

// Called every time a Run starts
void GamHitsEnergyWindowsActor::BeginOfRunAction(const G4Run *run) {
    if (run->GetRunID() == 0) {
        fThreadLocalData.Get().fIndex = 0;
        for (auto hc: fChannelHitsCollections) {
            DDD(hc->GetName());
            hc->InitializeRootTupleForWorker();
        }
    }
}

void GamHitsEnergyWindowsActor::BeginOfEventAction(const G4Event *) {
    // nothing
}

void GamHitsEnergyWindowsActor::EndOfEventAction(const G4Event *) {
    if (fInputHitsCollection == nullptr) {
        DDD("Create");
        auto hcm = GamHitsCollectionManager::GetInstance();
        fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
        // FIXME check attributes
    }
    auto &index = fThreadLocalData.Get().fIndex;
    auto n = fInputHitsCollection->GetSize() - index;
    // If no new hits, do nothing
    if (n <= 0) return;
    for (size_t i = 0; i < fChannelHitsCollections.size(); i++) {
        ApplyThreshold(fChannelHitsCollections[i], fChannelMin[i], fChannelMax[i]);
    }
    // update the hits index (thread local)
    index = fInputHitsCollection->GetSize();
}

void GamHitsEnergyWindowsActor::ApplyThreshold(GamHitsCollection *hc, double min, double max) {
    // prepare the vector of values
    auto &edep = fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit")->GetDValues();
    auto &pos = fInputHitsCollection->GetHitAttribute("PostPosition")->Get3Values();
    auto att_out_edep = hc->GetHitAttribute("TotalEnergyDeposit");
    auto att_out_pos = hc->GetHitAttribute("PostPosition");
    auto &index = fThreadLocalData.Get().fIndex;
    for (size_t i = index; i < fInputHitsCollection->GetSize(); i++) {
        auto e = edep[i];
        if (e >= min and e < max) {
            att_out_edep->FillDValue(e);
            att_out_pos->Fill3Value(pos[i]);
            //FillRemainingHitAttributes(i); // FIXME
        }
    }
}

// Called every time a Run ends
void GamHitsEnergyWindowsActor::EndOfRunAction(const G4Run *) {
    for (auto hc: fChannelHitsCollections) {
        DDD("Fill To Root");
        DDD(hc->GetName());
        DDD(hc->GetSize());
        hc->FillToRoot();
    }
}

// Called every time a Run ends
void GamHitsEnergyWindowsActor::EndOfSimulationWorkerAction(const G4Run *) {
    DDD("Write");
    for (auto hc: fChannelHitsCollections)
        hc->Write();
}

// Called when the simulation end
void GamHitsEnergyWindowsActor::EndSimulationAction() {
    for (auto hc: fChannelHitsCollections) {
        hc->Write();
        hc->Close();
    }
}

