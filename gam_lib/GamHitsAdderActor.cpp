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
    //Get the input hits collection
    auto hcm = GamHitsCollectionManager::GetInstance();
    fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
    if (not fInputHitsCollection->IsHitAttributeExists("TotalEnergyDeposit")) {
        std::ostringstream oss;
        oss << "Error GamHitsAdderActor needs a hit collection with a branch named 'TotalEnergyDeposit'. Abort";
        Fatal(oss.str());
    }
    if (not fInputHitsCollection->IsHitAttributeExists("PostPosition")) {
        std::ostringstream oss;
        oss << "Error GamHitsAdderActor needs a hit collection with a branch named 'PostPosition'. Abort";
        Fatal(oss.str());
    }

    // Create the output hits collection
    fOutputHitsCollection = hcm->NewHitsCollection(fOutputHitsCollectionName);
    fOutputHitsCollection->SetFilename(fOutputFilename);

    /*
     fOutputHitsCollection->InitializeHitAttributesFromCollection(fInputHitsCollection, fUserSkipHitAttributeNames);
     CheckAttribute(fOutputHitsCollection, "TotalEnergyDeposit");
     CheckAttribute(fOutputHitsCollection, "PostPosition");

     a = new AttributeListFiller()
     a->SetInputAttributes(fInputHitsCollection)
     a->SetOutputAttributes(fOutputHitsCollection)
     a->RemoveAttribute("TotalEnergyDeposit")
     a->RemoveAttribute("PostPosition")

     then a->FillAttributes(index)

     */


    std::set<std::string> names;
    names.insert("TotalEnergyDeposit");
    names.insert("PostPosition");
    // FIXME <- copy other attributes (if not skiped)
    for (auto att: fInputHitsCollection->GetHitAttributes()) {
        auto n = att->GetHitAttributeName();
        if (std::find(fUserSkipHitAttributeNames.begin(),
                      fUserSkipHitAttributeNames.end(), n) == fUserSkipHitAttributeNames.end())
            names.insert(n);
        DDD(n);
    }
    fOutputHitsCollection->InitializeHitAttributes(names);
    fOutputHitsCollection->InitializeRootTupleForMaster();
    fOutputEdepAttribute = fOutputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    fOutputPosAttribute = fOutputHitsCollection->GetHitAttribute("PostPosition");

    // structures to help computation
    for (auto att_name: names) {
        if (att_name == "TotalEnergyDeposit") continue;
        if (att_name == "PostPosition") continue;
        DDD(att_name);
        fRemainingInputHitAttributes.push_back(fInputHitsCollection->GetHitAttribute(att_name));
        fRemainingOutputHitAttributes.push_back(fOutputHitsCollection->GetHitAttribute(att_name));
    }

    names.erase("TotalEnergyDeposit");
    names.erase("PostPosition");
    fHitsAttributeFiller = new GamHitsAttributesFiller(fInputHitsCollection, fOutputHitsCollection, names);

    // debug
    mean_nb_event_per_hit = 0;
    auto att_edep = fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    auto att_pos = fInputHitsCollection->GetHitAttribute("PostPosition");
    fInputEdep = &att_edep->GetDValues();
    fInputPos = &att_pos->Get3Values();

}

// Called every time a Run starts
void GamHitsAdderActor::BeginOfRunAction(const G4Run *run) {
    if (run->GetRunID() == 0) {
        fOutputHitsCollection->InitializeRootTupleForWorker();
        fThreadLocalData.Get().fIndex = 0;
    }
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

    mean_nb_event_per_hit += n;

    // prepare the vector of values
    /*auto att_edep = fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    auto att_pos = fInputHitsCollection->GetHitAttribute("PostPosition");
    auto &edep = att_edep->GetDValues();
    auto &pos = att_pos->Get3Values();*/
    auto &edep = *fInputEdep;
    auto &pos = *fInputPos;

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
    //auto att_out_edep = fOutputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    //auto att_out_pos = fOutputHitsCollection->GetHitAttribute("PostPosition");
    if (sum_edep != 0) {
        // (both "Fill" calls are thread local)
        fOutputEdepAttribute->FillDValue(sum_edep);
        fOutputPosAttribute->Fill3Value(final_position);
        //FillRemainingHitAttributes(index); // FIXME
        fHitsAttributeFiller->Fill(index);
    }

    // update the hits index (thread local)
    fIndex = fInputHitsCollection->GetSize();
}

// Called every time a Run ends
void GamHitsAdderActor::EndOfRunAction(const G4Run *) {
    DDD("EndOfRunAction");
    DDD(mean_nb_event_per_hit);
    fOutputHitsCollection->FillToRoot();
}

// Called every time a Run ends
void GamHitsAdderActor::EndOfSimulationWorkerAction(const G4Run *) {
    DDD("EndOfSimulationWorkerAction");
    fOutputHitsCollection->Write();
}

// Called when the simulation end
void GamHitsAdderActor::EndSimulationAction() {
    DDD("EndSimulationAction");
    fOutputHitsCollection->Write();
    fOutputHitsCollection->Close();
}

void GamHitsAdderActor::FillRemainingHitAttributes(size_t index) {
    for (size_t i = 0; i < fRemainingOutputHitAttributes.size(); i++) {
        fRemainingOutputHitAttributes[i]->Fill(fRemainingInputHitAttributes[i], index);
    }
}
