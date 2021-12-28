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
    // Only required when MT
    if (G4Threading::IsMultithreadedApplication())
        fSingles->Write();
}

void GamSinglesCollectionActor::BeginOfEventAction(const G4Event *) {
    //DDD("GamSinglesCollectionActor::BeginOfEventAction");
}

void GamSinglesCollectionActor::EndOfEventAction(const G4Event *event) {
    // Cannot manage to Write to Root at EndOfEventAction in MT mode
    DDD("GamSinglesCollectionActor EndOfEventAction");
    if (fHits == nullptr) {
        DDD("get hits c");
        fHits = GamHitsCollectionManager::GetInstance()->GetHitsCollection("Hits");
    }
    DDD(event->GetEventID());
    auto ram = G4RootAnalysisManager::Instance();
    auto ntuple = ram->GetNtuple(fHits->GetTupleId());
    DDD(ntuple->entries());
    for(auto c : ntuple->columns()) {
          DDD(c->name());
          if (c->name() == "TotalEnergyDeposit") {
              auto l = c->get_leaf(); // seems ok ?
              DDD(l->length());
              auto & b = c->get_branch();
              DDD(b.entries());
              DDD(b.name());

              auto v = ntuple->find_column<double>(c->name());
              //auto cv = std::vector<double>(v->cast(8));
              //DDD(cv->size());
          }
    }
}

