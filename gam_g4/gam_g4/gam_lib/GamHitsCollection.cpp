/* --------------------------------------------------
   Copyright (C): OpenGam Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4Step.hh"
#include "GamHitsCollection.h"
#include "GamHitAttributeManager.h"
#include "GamHitsCollectionsRootManager.h"
#include "GamHitsCollectionIterator.h"


GamHitsCollection::GamHitsCollection(const std::string &collName) :
    G4VHitsCollection("", collName), fHitsCollectionName(collName) {
    fTupleId = -1;
    fHitsCollectionTitle = "Hits collection";
    fFilename = "";
    fCurrentHitAttributeId = 0;
    fWriteToRootFlag = true;
    threadLocalData.Get().fBeginOfEventIndex = 0;
}

GamHitsCollection::~GamHitsCollection() {
}

size_t GamHitsCollection::GetBeginOfEventIndex() const {
    return threadLocalData.Get().fBeginOfEventIndex;
}

void GamHitsCollection::SetBeginOfEventIndex(size_t index) {
    threadLocalData.Get().fBeginOfEventIndex = index;
}

void GamHitsCollection::SetBeginOfEventIndex() {
    SetBeginOfEventIndex(GetSize());
}

void GamHitsCollection::SetWriteToRootFlag(bool f) {
    fWriteToRootFlag = f;
}

void GamHitsCollection::SetFilename(std::string filename) {
    fFilename = filename;
    if (fFilename.empty()) SetWriteToRootFlag(false);
    else SetWriteToRootFlag(true);
}

void GamHitsCollection::InitializeHitAttributes(const std::vector<std::string> &names) {
    StartInitialization();
    for (const auto &name: names)
        InitializeHitAttribute(name);
    FinishInitialization();
}

void GamHitsCollection::InitializeHitAttributes(const std::set<std::string> &names) {
    StartInitialization();
    for (const auto &name: names)
        InitializeHitAttribute(name);
    FinishInitialization();
}

void GamHitsCollection::StartInitialization() {
    if (!fWriteToRootFlag) return;
    auto *am = GamHitsCollectionsRootManager::GetInstance();
    auto id = am->DeclareNewTuple(fHitsCollectionName);
    fTupleId = id;
}

void GamHitsCollection::InitializeRootTupleForMaster() {
    if (!fWriteToRootFlag) return;
    auto *am = GamHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
}

void GamHitsCollection::InitializeRootTupleForWorker() {
    if (!fWriteToRootFlag) return;
    // no need if not multi-thread
    if (not G4Threading::IsMultithreadedApplication()) return;
    auto *am = GamHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
    SetBeginOfEventIndex();
}

void GamHitsCollection::FillToRootIfNeeded(bool clear) {
    /*
        Policy :
        - can write to root or not according to the flag
        - can clear every N calls
     */
    if (!fWriteToRootFlag) {
        // need to set the index before (in case we don't clear)
        if (clear) Clear();
        else SetBeginOfEventIndex();
        return;
    }
    FillToRoot();
}

void GamHitsCollection::FillToRoot() {
    /*
     * maybe not very efficient to loop that way (row then column)
     * but I don't manage to do elsewhere
     */
    auto *am = GamHitsCollectionsRootManager::GetInstance();
    for (size_t i = 0; i < GetSize(); i++) {
        for (auto *att: fHitAttributes) {
            att->FillToRoot(i);
        }
        am->AddNtupleRow(fTupleId);
    }
    // required ! Cannot fill without clear
    Clear();
}

void GamHitsCollection::Clear() {
    for (auto *att: fHitAttributes) {
        att->Clear();
    }
    SetBeginOfEventIndex(0);
}

void GamHitsCollection::Write() const {
    if (!fWriteToRootFlag) return;
    auto *am = GamHitsCollectionsRootManager::GetInstance();
    am->Write(fTupleId);
}

void GamHitsCollection::Close() const {
    if (!fWriteToRootFlag) return;
    auto *am = GamHitsCollectionsRootManager::GetInstance();
    am->CloseFile(fTupleId);
}

void GamHitsCollection::InitializeHitAttribute(const std::string &name) {
    if (fHitAttributeMap.find(name) != fHitAttributeMap.end()) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' is already initialized. Abort";
        Fatal(oss.str());
    }
    auto *att = GamHitAttributeManager::GetInstance()->NewHitAttribute(name);
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
    // Finally, not useful (yet?)
}

void GamHitsCollection::FillHits(G4Step *step) {
    for (auto *att: fHitAttributes) {
        att->ProcessHits(step);
    }
}

void GamHitsCollection::FillHitsWithEmptyValue() {
    for (auto *att: fHitAttributes) {
        att->FillHitWithEmptyValue();
    }
}

size_t GamHitsCollection::GetSize() const {
    if (fHitAttributes.empty()) return 0;
    return fHitAttributes[0]->GetSize();
}

GamVHitAttribute *GamHitsCollection::GetHitAttribute(const std::string &name) {
    // Sometimes it is faster to apologize instead of asking permission ...
    try {
        return fHitAttributeMap.at(name);
    } catch (std::out_of_range &) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' does not exist. Abort";
        Fatal(oss.str());
    }
    return nullptr; // fake to avoid warning
}

bool GamHitsCollection::IsHitAttributeExists(const std::string &name) const {
    return (fHitAttributeMap.count(name) != 0);
}


std::set<std::string> GamHitsCollection::GetHitAttributeNames() const {
    std::set<std::string> list;
    for (auto *att: fHitAttributes)
        list.insert(att->GetHitAttributeName());
    return list;
}

GamHitsCollection::Iterator GamHitsCollection::NewIterator() {
    return {this, 0};
}

std::string GamHitsCollection::DumpLastHit() const {
    std::ostringstream oss;
    int n = GetSize() - 1;
    for (auto *att: fHitAttributes) {
        oss << att->GetHitAttributeName() << " = " << att->Dump(n) << "  ";
    }
    return oss.str();
}
