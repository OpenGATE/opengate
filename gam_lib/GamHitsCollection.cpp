/* --------------------------------------------------
   Copyright (C): OpenGam Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitsCollection.h"
#include "GamHitAttributeManager.h"
#include "G4RootAnalysisManager.hh"

GamHitsCollection::GamHitsCollection(std::string collName) :
    G4VHitsCollection(), fHitsCollectionName(collName) {
    DDD(collName);
    fRootTupleId = -1;
    fHitsCollectionTitle = "Hits collection";
    fFilename = "hits_collection.root";
    DDD("constructor GamHitsCollection");
}

GamHitsCollection::~GamHitsCollection() {
}


void GamHitsCollection::SetFilename(std::string filename) {
    fFilename = filename;
}

void GamHitsCollection::StartInitialization() {
    DDD("GamHitsCollection StartInitialization");
    auto am = GamHitAttributeManager::GetInstance();
    DDD(fFilename);
    am->OpenFile(fFilename);
    auto ram = G4RootAnalysisManager::Instance();
    DDD(fHitsCollectionName);
    auto n = G4Threading::G4GetThreadId();
    fRootTupleId = ram->CreateNtuple(fHitsCollectionName, fHitsCollectionTitle);
    DDD(fRootTupleId);
    if (fRootTupleId == -1) {
        for (auto i = 0; i < ram->GetNofNtuples(); i++) {
            DDD(i);
            auto tuple = ram->GetNtuple(i);
            tuple->print_columns(std::cout);
        }
    }
    else {
        am->fTupleNameIdMap[fHitsCollectionName] = fRootTupleId;
    }
    // FIXME if -1, because MT, how to get the tupleID ???
    fRootTupleId = 0; // FIXME
    am->AddTupleId(fRootTupleId);
}

void GamHitsCollection::Write() {
    DDD("Write");
    auto ram = G4RootAnalysisManager::Instance();
    ram->Write();
}

void GamHitsCollection::Close() {
    auto am = GamHitAttributeManager::GetInstance();
    am->CloseFile(fRootTupleId);
}

void GamHitsCollection::InitializeHitAttribute(std::string name) {
    DDD("InitializeHitAttribute");
    DDD(name);

    if (fHitAttributeMap.find(name) != fHitAttributeMap.end()) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' is already initialized. Abort";
        Fatal(oss.str());
    }

    // If this is the first attribute, create the root collection
    //if (fHitAttributes.size() == 0) StartInitialization();

    // set branch id
    auto ram = G4RootAnalysisManager::Instance();
    auto att = GamHitAttributeManager::GetInstance()->NewHitAttribute(name);
    fHitAttributes.push_back(att);
    fHitAttributeMap[name] = att;
    // FIXME depends on the type -> todo in the HitAttribute ?
    auto n = G4Threading::G4GetThreadId();
    att->fHitAttributeId = ram->CreateNtupleDColumn(fRootTupleId, name);
    DDD(att->fHitAttributeId);
    att->fRootTupleId = fRootTupleId;
    DDD(att->fRootTupleId);
}

void GamHitsCollection::FinishInitialization() {
    auto ram = G4RootAnalysisManager::Instance();
    auto n = G4Threading::G4GetThreadId();
    ram->FinishNtuple(fRootTupleId);
}


void GamHitsCollection::ProcessHits(G4Step *step, G4TouchableHistory *touchable) {
    auto ram = G4RootAnalysisManager::Instance();
    for (auto att: fHitAttributes) {
        //DDD(att->fHitAttributeName);
        att->ProcessHits(step, touchable);
    }

    // root tuple
    //DDD("AddNtupleRow");
    //DDD(fRootTupleId);
    ram->AddNtupleRow(fRootTupleId);
    //ram->Write(); // This will be managed in the Actor.
    //Write();
}