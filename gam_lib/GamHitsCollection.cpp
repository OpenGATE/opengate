/* --------------------------------------------------
   Copyright (C): OpenGam Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitsCollection.h"
#include "GamHitAttributeManager.h"


G4Mutex GamHitsCollectionMutex = G4MUTEX_INITIALIZER; // FIXME

GamHitsCollection::GamHitsCollection(std::string collName) :
    G4VHitsCollection("", collName), fHitsCollectionName(collName) {
    DDD("constructor GamHitsCollection");
    DDD(collName);
    fTupleId = -1;
    fHitsCollectionTitle = "Hits collection";
    fFilename = "hits.root";
}

GamHitsCollection::~GamHitsCollection() {
}


void GamHitsCollection::SetFilename(std::string filename) {
    fFilename = filename;
}

void GamHitsCollection::StartInitialization() {
    DDD("GamHitsCollection StartInitialization");
    auto am = GamHitAttributeManager::GetInstance();
    auto id = am->DeclareNewTuple(fHitsCollectionName);
    fTupleId = id;
}

void GamHitsCollection::Write() {
    auto am = GamHitAttributeManager::GetInstance();
    am->Write();
}

void GamHitsCollection::Close() {
    auto am = GamHitAttributeManager::GetInstance();
    am->CloseFile(fTupleId);
}

void GamHitsCollection::InitializeHitAttribute(std::string name) {
    DDD("InitializeHitAttribute");
    if (fHitAttributeMap.find(name) != fHitAttributeMap.end()) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' is already initialized. Abort";
        Fatal(oss.str());
    }
    auto att = GamHitAttributeManager::GetInstance()->NewHitAttribute(name);
    fHitAttributes.push_back(att);
    fHitAttributeMap[name] = att;
    // FIXME depends on the type -> todo in the HitAttribute ?
    att->fHitAttributeId = fHitAttributes.size() - 1;
    att->fRootTupleId = fTupleId;
}

void GamHitsCollection::FinishInitialization() {
    // Finally, not useful
}

void GamHitsCollection::ProcessHits(G4Step *step, G4TouchableHistory *touchable) {
    G4AutoLock mutex(&GamHitsCollectionMutex);
    auto am = GamHitAttributeManager::GetInstance();
    for (auto att: fHitAttributes) {
        att->ProcessHits(step, touchable);
    }
    am->AddNtupleRow(fTupleId);
}