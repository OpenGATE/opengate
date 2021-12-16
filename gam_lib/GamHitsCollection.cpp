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
    fFilename = "hits.root";
    DDD("constructor GamHitsCollection");
    fNHits = 0;
}

GamHitsCollection::~GamHitsCollection() {
}


void GamHitsCollection::SetFilename(std::string filename) {
    fFilename = filename;
}

bool GamHitsCollection::StartInitialization() {
    DDD("GamHitsCollection StartInitialization");
    auto am = GamHitAttributeManager::GetInstance();

    /* if (am->fTupleNameIdMap.count(fHitsCollectionName)) {
         auto threads = am->fBuildForThisThreadMap[fHitsCollectionName];
         DDD("The tuple already exist, check if need to be build or not for this thread");
         DDD(fHitsCollectionName);
         auto n = G4Threading::G4GetThreadId();
         DDD(n);
         const bool is_in = threads.find(n) != threads.end();
         DDD(is_in);
         if (is_in) return false;
         DDD("not build for this thread  -> continue");
     }*/

    /*    DDD(fFilename);
    am->OpenFile(fFilename);
    auto ram = G4RootAnalysisManager::Instance();
    ram->SetVerboseLevel(0);
    DDD(fHitsCollectionName);
    auto n = G4Threading::G4GetThreadId();
    fRootTupleId = ram->CreateNtuple(fHitsCollectionName, fHitsCollectionTitle);
    DDD(fRootTupleId);
    */

    auto id = am->DeclareNewTuple(fHitsCollectionName);
    DDD(id);

    //am->fTupleNameIdMap[fHitsCollectionName] = fRootTupleId;
    //am->fMasterIsBuilt[fHitsCollectionName] = true;
    //am->fBuildForThisThreadMap[fHitsCollectionName].insert(n); // FIXME replace by master or workers ?
    //am->InsertTupleId(fRootTupleId);
    fRootTupleId = id;
    return true;
}

void GamHitsCollection::Write() {
    DDD("Write");
    auto ram = G4RootAnalysisManager::Instance();
    DDD(ram);
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
    //auto ram = G4RootAnalysisManager::Instance();
    auto att = GamHitAttributeManager::GetInstance()->NewHitAttribute(name);
    fHitAttributes.push_back(att);
    fHitAttributeMap[name] = att;
    // FIXME depends on the type -> todo in the HitAttribute ?
    //auto n = G4Threading::G4GetThreadId();
    //att->fHitAttributeId = ram->CreateNtupleDColumn(fRootTupleId, name);
    att->fHitAttributeId = fHitAttributes.size()-1;
    DDD(att->fHitAttributeId);
    att->fRootTupleId = fRootTupleId;
    DDD(att->fRootTupleId);
}

void GamHitsCollection::FinishInitialization() {
    auto ram = G4RootAnalysisManager::Instance();
    auto n = G4Threading::G4GetThreadId();
    //ram->FinishNtuple(fRootTupleId);
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

    // DEBUG
    fNHits++;
}