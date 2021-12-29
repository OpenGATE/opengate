/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <iostream>
#include "GamSinglesCollectionActor.h"
#include "GamDictHelpers.h"
#include "GamHitsCollectionManager.h"
#include "GamHitAttributeManager.h"
#include "G4RootAnalysisManager.hh"

GamSinglesCollectionActor::GamSinglesCollectionActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfEventAction");
    fOutputFilename = DictStr(user_info, "output");
    fSinglesCollectionName = DictStr(user_info, "name");
    fSingles = nullptr;
    fHits = nullptr;
    fIndex = 0;
}

GamSinglesCollectionActor::~GamSinglesCollectionActor() {
}

// Called when the simulation start
void GamSinglesCollectionActor::StartSimulationAction() {
    fSingles = GamHitsCollectionManager::GetInstance()->NewHitsCollection(fSinglesCollectionName);
    fSingles->SetFilename(fOutputFilename);
    //auto ham = GamHitAttributeManager::GetInstance();
    std::vector<std::string> names;
    names.push_back("TotalEnergyDeposit"); // same name but no stepping action
    fSingles->InitializeHitAttributes(names);
    fSingles->CreateRootTupleForMaster();
}

// Called when the simulation end
void GamSinglesCollectionActor::EndSimulationAction() {
    fSingles->Write();
    fSingles->Close();
}

// Called every time a Run starts
void GamSinglesCollectionActor::BeginOfRunAction(const G4Run *) {
    fSingles->CreateRootTupleForWorker();
    fIndex = 0;
}

// Called every time a Run ends
void GamSinglesCollectionActor::EndOfRunAction(const G4Run *) {
    fSingles->FillToRoot();
    // Only required when MT
    if (G4Threading::IsMultithreadedApplication())
        fSingles->Write();
}

void GamSinglesCollectionActor::BeginOfEventAction(const G4Event *) {
    //DDD("GamSinglesCollectionActor::BeginOfEventAction");
}

void GamSinglesCollectionActor::EndOfEventAction(const G4Event *) {
    // Cannot manage to Write to Root at EndOfEventAction in MT mode
    //DDD("GamSinglesCollectionActor EndOfEventAction");
    if (fHits == nullptr) {
        DDD("get hits c");
        fHits = GamHitsCollectionManager::GetInstance()->GetHitsCollection("Hits");
    }
    auto n = fHits->GetSize() - fIndex;
    DDD(n);
    if (n != 0) {
        auto att_in = fHits->GetHitAttribute("TotalEnergyDeposit");
        double sum = 0.0;
        auto values = att_in->GetDValues();
        DDD(values.size());
        for (size_t i = 0; i < n; i++) {
            sum += values[i];
        }
        auto att_out = fSingles->GetHitAttribute("TotalEnergyDeposit");
        att_out->FillDValue(sum);
        DDD(sum);
        fIndex = fHits->GetSize() - 1;
    }
}

