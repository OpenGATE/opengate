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

GamHitsAdderActor::GamHitsAdderActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictStr(user_info, "output");
    fOutputHitsCollectionName = DictStr(user_info, "name");
    fInputHitsCollectionName = DictStr(user_info, "input_hits_collection");
    fUserSkipHitAttributeNames = DictVecStr(user_info, "skip_attributes");
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
    fThreadLocalData.Get().fIndex = 0;
}

GamHitsAdderActor::~GamHitsAdderActor() {
}

// Called when the simulation start
void GamHitsAdderActor::StartSimulationAction() {
    DDD("StartSimulationAction");
    //Get the input hits collection
    auto hcm = GamHitsCollectionManager::GetInstance();
    fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
    CheckThatAttributeExists(fInputHitsCollection, "TotalEnergyDeposit");
    CheckThatAttributeExists(fInputHitsCollection, "PostPosition");

    // Create the list of output attributes
    auto names = fInputHitsCollection->GetHitAttributeNames();
    for (auto n: fUserSkipHitAttributeNames) {
        DDD(n);
        if (names.count(n) > 0)
            names.erase(n);
    }
    DDD(names.size());
    for (auto n: names) {DDD(n); }

    // Create the output hits collection with the same list of attributes
    fOutputHitsCollection = hcm->NewHitsCollection(fOutputHitsCollectionName);
    fOutputHitsCollection->SetFilename(fOutputFilename);
    DDD(fOutputFilename);
    fOutputHitsCollection->InitializeHitAttributes(names);
    fOutputHitsCollection->InitializeRootTupleForMaster();


}

// Called every time a Run starts
void GamHitsAdderActor::BeginOfRunAction(const G4Run *run) {
    DDD(run->GetRunID());
    if (run->GetRunID() == 0) {
        fOutputHitsCollection->InitializeRootTupleForWorker();
        // Init a Filler of all others attributes
        auto names = fOutputHitsCollection->GetHitAttributeNames();
        names.erase("TotalEnergyDeposit");
        names.erase("PostPosition");
        DDD(names.size());
        for (auto n: names) {DDD(n); }
        DDD(names.size());
        fThreadLocalData.Get().fHitsAttributeFiller = new GamHitsAttributesFiller(fInputHitsCollection,
                                                                                  fOutputHitsCollection, names);

        // set pointers to the attributes needed for computation
        fThreadLocalData.Get().fOutputEdepAttribute = fOutputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
        fThreadLocalData.Get().fOutputPosAttribute = fOutputHitsCollection->GetHitAttribute("PostPosition");

        // used during computation (not thread local)
        auto att_edep = fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
        auto att_pos = fInputHitsCollection->GetHitAttribute("PostPosition");
        fThreadLocalData.Get().fInputEdep = &att_edep->GetDValues();
        fThreadLocalData.Get().fInputPos = &att_pos->Get3Values();
        DDD(fThreadLocalData.Get().fInputEdep->size());
        DDD(fThreadLocalData.Get().fInputPos->size());

    }
    // reset index (because fill to root at end of run)
    fThreadLocalData.Get().fIndex = 0;
}

void GamHitsAdderActor::BeginOfEventAction(const G4Event *) {
    // nothing
}

void GamHitsAdderActor::EndOfEventAction(const G4Event *) {
    // Consider all hits in the current event, sum their energy and estimate the position
    auto &fIndex = fThreadLocalData.Get().fIndex;
    auto n = fInputHitsCollection->GetSize() - fIndex;

    // If no new hits, do nothing
    if (n <= 0) return;

    // prepare the vector of values
    auto &edep = *fThreadLocalData.Get().fInputEdep;
    auto &pos = *fThreadLocalData.Get().fInputPos;

    // initialize the energy and the position
    double sum_edep = 0;
    G4ThreeVector final_position(0);
    size_t index = fIndex;

    // loop on all hits during this event
    if (fPolicy == AdderPolicy::TakeEnergyWinner) {
        for (size_t i = fIndex; i < fInputHitsCollection->GetSize(); i++) {
            auto e = edep[i];
            if (e == 0) continue; // ignore if no deposited energy
            if (e > sum_edep) final_position = pos[i];
            sum_edep += e;
            index = i; // keep the 'winner' index
        }
    } else {
        // Policy is TakeEnergyCentroid (energy weighted position)
        for (size_t i = fIndex; i < fInputHitsCollection->GetSize(); i++) {
            auto e = edep[i];
            if (e == 0) continue;// ignore if no deposited energy
            final_position += pos[i] * e;
            sum_edep += e;
            index = i; // keep the last seen index FIXME
        }
        if (sum_edep != 0)
            final_position = final_position / sum_edep;
    }

    // create the output hits collection
    if (sum_edep != 0) {
        // (all "Fill" calls are thread local)
        fThreadLocalData.Get().fOutputEdepAttribute->FillDValue(sum_edep);
        fThreadLocalData.Get().fOutputPosAttribute->Fill3Value(final_position);
        fThreadLocalData.Get().fHitsAttributeFiller->Fill(index);
    }

    // update the hits index (thread local)
    fIndex = fInputHitsCollection->GetSize();
}

// Called every time a Run ends
void GamHitsAdderActor::EndOfRunAction(const G4Run *) {
    fOutputHitsCollection->FillToRoot();
}

// Called every time a Run ends
void GamHitsAdderActor::EndOfSimulationWorkerAction(const G4Run *) {
    fOutputHitsCollection->Write();
}

// Called when the simulation end
void GamHitsAdderActor::EndSimulationAction() {
    fOutputHitsCollection->Write();
    fOutputHitsCollection->Close();
}

