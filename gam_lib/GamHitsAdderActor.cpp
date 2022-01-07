/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <iostream>
#include "GamHitsAdderActor.h"
#include "GamDictHelpers.h"
#include "GamHitsCollectionManager.h"
#include "GamHitAttributeManager.h"
#include "G4RootAnalysisManager.hh"

GamHitsAdderActor::GamHitsAdderActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfEventAction");
    fOutputFilename = DictStr(user_info, "output");
    fOutputHitsCollectionName = DictStr(user_info, "name");
    fInputHitsCollectionName = DictStr(user_info, "input_hits_collection");
    fPolicy = AdderPolicy::Error;
    auto policy = DictStr(user_info, "policy");
    if (policy == "TakeEnergyWinner") fPolicy = AdderPolicy::TakeEnergyWinner;
    else if (policy == "TakeEnergyCentroid") fPolicy = AdderPolicy::TakeEnergyCentroid;
    if (fPolicy == AdderPolicy::Error) {
        std::ostringstream oss;
        oss << "Error in GamHitsAdderActor: unknown policy. Must be TakeEnergyWinner or TakeEnergyCentroid"
            << " while '" << policy << "' is read.";
        Fatal(oss.str());
    }
    fOutputHitsCollection = nullptr;
    fInputHitsCollection = nullptr;
    fIndex = 0;
}

GamHitsAdderActor::~GamHitsAdderActor() {
}

// Called when the simulation start
void GamHitsAdderActor::StartSimulationAction() {
    // Create the output hits collection
    fOutputHitsCollection = GamHitsCollectionManager::GetInstance()->NewHitsCollection(fOutputHitsCollectionName);
    fOutputHitsCollection->SetFilename(fOutputFilename);
    std::vector<std::string> names;
    names.push_back("TotalEnergyDeposit"); // same name but no stepping action
    names.push_back("PostPosition"); // same name but no stepping action
    fOutputHitsCollection->InitializeHitAttributes(names);
    fOutputHitsCollection->CreateRootTupleForMaster();
}

// Called when the simulation end
void GamHitsAdderActor::EndSimulationAction() {
    fOutputHitsCollection->Write();
    fOutputHitsCollection->Close();
}

// Called every time a Run starts
void GamHitsAdderActor::BeginOfRunAction(const G4Run *) {
    fOutputHitsCollection->CreateRootTupleForWorker();
    fIndex = 0;
}

// Called every time a Run ends
void GamHitsAdderActor::EndOfRunAction(const G4Run *) {
    fOutputHitsCollection->FillToRoot();
    // Only required when MT
    if (G4Threading::IsMultithreadedApplication())
        fOutputHitsCollection->Write();
    fIndex = 0;
}

void GamHitsAdderActor::BeginOfEventAction(const G4Event *) {
    //DDD("GamHitsAdderActor::BeginOfEventAction");
}

void GamHitsAdderActor::EndOfEventAction(const G4Event *) {
    if (fInputHitsCollection == nullptr) {
        // First time only, we retrive the input hits collection
        auto hcm = GamHitsCollectionManager::GetInstance();
        fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
    }
    // Consider all hits in the current event, sum their energy and estimate the position
    auto n = fInputHitsCollection->GetSize() - fIndex;
    if (n <= 0) return;

    // get the vector of values
    auto att_edep = fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    auto att_pos = fInputHitsCollection->GetHitAttribute("PostPosition");
    auto edep = att_edep->GetDValues();
    auto pos = att_pos->Get3Values();

    // initialize the energy and the position
    double sum_edep = 0;
    G4ThreeVector final_position(0);

    // loop on all hits during this event
    if (fPolicy == AdderPolicy::TakeEnergyWinner) {
        for (size_t i = fIndex; i < fInputHitsCollection->GetSize(); i++) {
            auto e = edep[i];
            if (e == 0) continue;
            if (e > sum_edep) final_position = pos[i];
            sum_edep += e;
        }
    } else {
        // Policy is TakeEnergyCentroid (energy weighted position)
        for (size_t i = fIndex; i < fInputHitsCollection->GetSize(); i++) {
            auto e = edep[i];
            if (e == 0) continue;
            final_position += pos[i] * e;
            sum_edep += e;
        }
        if (sum_edep != 0)
            final_position = final_position / sum_edep;
    }

    // create the output hits collection
    auto att_out_edep = fOutputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    auto att_out_pos = fOutputHitsCollection->GetHitAttribute("PostPosition");
    if (sum_edep != 0) {
        att_out_edep->FillDValue(sum_edep);
        att_out_pos->Fill3Value(final_position);
    }

    // update the hits index;
    fIndex = fInputHitsCollection->GetSize();
}

