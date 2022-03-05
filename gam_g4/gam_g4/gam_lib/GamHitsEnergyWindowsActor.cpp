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
    fActions.insert("StartSimulationAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictStr(user_info, "output");
    fInputHitsCollectionName = DictStr(user_info, "input_hits_collection");
    fUserSkipHitAttributeNames = DictVecStr(user_info, "skip_attributes");
    // Get information for all channels
    auto dv = DictVecDict(user_info, "channels");
    for (auto d: dv) {
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
    // Get input hits collection
    auto hcm = GamHitsCollectionManager::GetInstance();
    fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
    CheckThatAttributeExists(fInputHitsCollection, "TotalEnergyDeposit");
    // Create the list of output attributes
    auto names = fInputHitsCollection->GetHitAttributeNames();
    for (auto n: fUserSkipHitAttributeNames)
        if (names.count(n) > 0)
            names.erase(n);
    // Create the output hits collections (one for each energy window channel)
    for (auto name: fChannelNames) {
        auto hc = hcm->NewHitsCollection(name);
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
        for (auto hc: fChannelHitsCollections) {
            // Init a Filler of all others attributes (all except edep and pos)
            auto f = new GamHitsAttributesFiller(fInputHitsCollection, hc, hc->GetHitAttributeNames());
            l.fFillers.push_back(f);
        }
        for (auto hc: fChannelHitsCollections) {
            hc->InitializeRootTupleForWorker();
        }
        l.fInputEdep = &fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit")->GetDValues();
    }
    l.fIndex = 0;
}


void GamHitsEnergyWindowsActor::EndOfEventAction(const G4Event *) {
    auto &index = fThreadLocalData.Get().fIndex;
    auto n = fInputHitsCollection->GetSize() - index;
    // If no new hits, do nothing
    if (n <= 0) return;
    for (size_t i = 0; i < fChannelHitsCollections.size(); i++) {
        ApplyThreshold(i, fChannelMin[i], fChannelMax[i]);
    }
    // update the hits index (thread local)
    index = fInputHitsCollection->GetSize();
}

void GamHitsEnergyWindowsActor::ApplyThreshold(size_t i, double min, double max) {
    auto &l = fThreadLocalData.Get();
    // get the vector of values
    auto &edep = *l.fInputEdep;
    auto &index = l.fIndex;
    for (size_t n = index; n < fInputHitsCollection->GetSize(); n++) {
        auto e = edep[n];
        if (e >= min and e < max) {
            l.fFillers[i]->Fill(index);
        }
    }
}

// Called every time a Run ends
void GamHitsEnergyWindowsActor::EndOfRunAction(const G4Run *) {
    for (auto hc: fChannelHitsCollections)
        hc->FillToRoot();
}

// Called every time a Run ends
void GamHitsEnergyWindowsActor::EndOfSimulationWorkerAction(const G4Run *) {
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

