/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <iostream>
#include "GamHitsEnergyWindowsActor.h"
#include "GamHelpersDict.h"
#include "GamHitsCollectionManager.h"

GamHitsEnergyWindowsActor::GamHitsEnergyWindowsActor(py::dict &user_info)
    : GamVActor(user_info) {
    // actions
    fActions.insert("StartSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("BeginOfEventAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");

    // options
    fOutputFilename = DictGetStr(user_info, "output");
    fInputHitsCollectionName = DictGetStr(user_info, "input_hits_collection");
    fUserSkipHitAttributeNames = DictGetVecStr(user_info, "skip_attributes");
    fClearEveryNEvents = DictGetInt(user_info, "clear_every");

    // Get information for all channels
    auto dv = DictGetVecDict(user_info, "channels");
    for (auto d: dv) {
        fChannelNames.push_back(DictGetStr(d, "name"));
        fChannelMin.push_back(DictGetDouble(d, "min"));
        fChannelMax.push_back(DictGetDouble(d, "max"));
    }

    // init
    fInputHitsCollection = nullptr;
}

GamHitsEnergyWindowsActor::~GamHitsEnergyWindowsActor() {
}


// Called when the simulation start
void GamHitsEnergyWindowsActor::StartSimulationAction() {
    // Get input hits collection
    auto *hcm = GamHitsCollectionManager::GetInstance();
    fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
    CheckRequiredAttribute(fInputHitsCollection, "TotalEnergyDeposit");
    // Create the list of output attributes
    auto names = fInputHitsCollection->GetHitAttributeNames();
    for (const auto &n: fUserSkipHitAttributeNames) {
        if (names.count(n) > 0)
            names.erase(n);
    }
    // Create the output hits collections (one for each energy window channel)
    for (const auto &name: fChannelNames) {
        auto *hc = hcm->NewHitsCollection(name);
        hc->SetFilename(fOutputFilename);
        hc->InitializeHitAttributes(names);
        hc->InitializeRootTupleForMaster();
        fChannelHitsCollections.push_back(hc);
    }
}

void GamHitsEnergyWindowsActor::BeginOfRunAction(const G4Run *run) {
    auto &l = fThreadLocalData.Get();
    if (run->GetRunID() == 0) {
        // Create the output hits collections (one for each energy window channel)
        for (auto *hc: fChannelHitsCollections) {
            // Init a Filler of all others attributes (all except edep and pos)
            auto *f = new GamHitsAttributesFiller(fInputHitsCollection, hc, hc->GetHitAttributeNames());
            l.fFillers.push_back(f);
        }
        for (auto *hc: fChannelHitsCollections) {
            hc->InitializeRootTupleForWorker();
        }
        l.fInputEdep = &fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit")->GetDValues();
    }
}

void GamHitsEnergyWindowsActor::BeginOfEventAction(const G4Event *event) {
    bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
    for (auto *hc: fChannelHitsCollections) {
        hc->FillToRootIfNeeded(must_clear);
    }
    fThreadLocalData.Get().fLastEnergyWindowId = -1;
}

void GamHitsEnergyWindowsActor::EndOfEventAction(const G4Event * /*event*/) {
    auto index = fInputHitsCollection->GetBeginOfEventIndex();
    auto n = fInputHitsCollection->GetSize() - index;
    // If no new hits, do nothing
    if (n <= 0) return;
    // init last energy windows to 'outside' (-1)
    for (size_t i = 0; i < fChannelHitsCollections.size(); i++) {
        ApplyThreshold(i, fChannelMin[i], fChannelMax[i]);
    }
}

void GamHitsEnergyWindowsActor::ApplyThreshold(size_t i, double min, double max) {
    auto &l = fThreadLocalData.Get();
    // get the vector of values
    auto &edep = *l.fInputEdep;
    // get the index of the first hit for this event
    auto index = fInputHitsCollection->GetBeginOfEventIndex();
    // fill all the hits
    for (size_t n = index; n < fInputHitsCollection->GetSize(); n++) {
        auto e = edep[n];
        if (e >= min and e < max) { // FIXME put in doc. strictly or not ?
            l.fFillers[i]->Fill(index);
            l.fLastEnergyWindowId = i;
        }
    }
}

int GamHitsEnergyWindowsActor::GetLastEnergyWindowId() {
    return fThreadLocalData.Get().fLastEnergyWindowId;
}

// Called every time a Run ends
void GamHitsEnergyWindowsActor::EndOfRunAction(const G4Run * /*run*/) {
    for (auto *hc: fChannelHitsCollections)
        hc->FillToRootIfNeeded(true);
}

// Called every time a Run ends
void GamHitsEnergyWindowsActor::EndOfSimulationWorkerAction(const G4Run * /*run*/) {
    for (auto *hc: fChannelHitsCollections)
        hc->Write();
}

// Called when the simulation end
void GamHitsEnergyWindowsActor::EndSimulationAction() {
    for (auto *hc: fChannelHitsCollections) {
        hc->Write();
        hc->Close();
    }
}

