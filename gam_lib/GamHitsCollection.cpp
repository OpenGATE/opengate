/* --------------------------------------------------
   Copyright (C): OpenGam Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitsCollection.h"
#include "GamHitAttributeManager.h"
#include "GamHitsCollectionsRootManager.h"


G4Mutex GamHitsCollectionMutex = G4MUTEX_INITIALIZER;

GamHitsCollection::GamHitsCollection(std::string collName) :
    G4VHitsCollection("", collName), fHitsCollectionName(collName) {
    fTupleId = -1;
    fHitsCollectionTitle = "Hits collection";
    fFilename = "hits.root";
    fCurrentHitAttributeId = 0;
}

GamHitsCollection::~GamHitsCollection() {
}


void GamHitsCollection::SetFilename(std::string filename) {
    fFilename = filename;
}

void GamHitsCollection::InitializeHitAttributes(const std::vector<std::string> &names) {
    StartInitialization();
    for (auto &name: names)
        InitializeHitAttribute(name);
    FinishInitialization();
}

void GamHitsCollection::StartInitialization() {
    auto am = GamHitsCollectionsRootManager::GetInstance();
    auto id = am->DeclareNewTuple(fHitsCollectionName);
    fTupleId = id;
}

void GamHitsCollection::CreateRootTupleForMaster() {
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
}

void GamHitsCollection::CreateRootTupleForWorker() {
    // no need if not multi-thread
    if (not G4Threading::IsMultithreadedApplication()) return;
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
}

void GamHitsCollection::FillToRoot(bool clear) {
    /*
     * maybe not very efficient to loop that way (row then column)
     * but I don't manage to do elsewhere
     */
    auto am = GamHitsCollectionsRootManager::GetInstance();
    for (size_t i = 0; i < GetSize(); i++) {
        for (auto att: fHitAttributes) {
            att->FillToRoot(i);
        }
        am->AddNtupleRow(fTupleId);
    }
    // Clear the values once they are filled to root
    // (unsure if useful to not clean)
    if (clear) Clear();
}

void GamHitsCollection::Clear() {
    for (auto att: fHitAttributes) {
        att->Clear();
    }
}

void GamHitsCollection::Write() {
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->Write(fTupleId);
}

void GamHitsCollection::Close() {
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->CloseFile(fTupleId);
}

void GamHitsCollection::InitializeHitAttribute(std::string name) {
    if (fHitAttributeMap.find(name) != fHitAttributeMap.end()) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' is already initialized. Abort";
        Fatal(oss.str());
    }
    auto att = GamHitAttributeManager::GetInstance()->NewHitAttribute(name); // FIXME store HC ?
    fHitAttributes.push_back(att);
    fHitAttributeMap[name] = att;
    att->SetHitAttributeId(fCurrentHitAttributeId);
    att->SetTupleId(fTupleId);
    fCurrentHitAttributeId++;
    // special case for type=3
    if (att->GetHitAttributeType() == '3')
        fCurrentHitAttributeId += 2;
}

void GamHitsCollection::FinishInitialization() {
    // Finally, not useful
}

void GamHitsCollection::ProcessHits(G4Step *step, G4TouchableHistory *touchable) {
    // Unsure if mutex is more efficient here or for each attribute
    G4AutoLock mutex(&GamHitsCollectionMutex);
    for (auto att: fHitAttributes) {
        att->ProcessHits(step, touchable);
    }
}

size_t GamHitsCollection::GetSize() const {
    if (fHitAttributes.empty()) return 0;
    return fHitAttributes[0]->GetSize();
}

GamVHitAttribute *GamHitsCollection::GetHitAttribute(const std::string &name) {
    if (fHitAttributeMap.count(name) == 0) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' does not exist. Abort";
        Fatal(oss.str());
    }
    return fHitAttributeMap[name];
}
