/* --------------------------------------------------
   Copyright (C): OpenGam Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitsCollection.h"
#include "GamHitAttributeManager.h"
#include "GamHitsCollectionsRootManager.h"

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

void GamHitsCollection::InitializeHitAttributes(std::vector<std::string> names) {
    StartInitialization();
    for (auto name: names)
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

void GamHitsCollection::Write() {
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->Write();
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
    for (auto att: fHitAttributes) {
        att->ProcessHits(step, touchable);
    }
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->AddNtupleRow(fTupleId);
}