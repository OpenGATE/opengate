/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4Step.hh"
#include "GateHitsCollection.h"
#include "GateHitAttributeManager.h"
#include "GateHitsCollectionsRootManager.h"
#include "GateHitsCollectionIterator.h"


GateHitsCollection::GateHitsCollection(const std::string &collName) :
    G4VHitsCollection("", collName), fHitsCollectionName(collName) {
    fTupleId = -1;
    fHitsCollectionTitle = "Hits collection";
    fFilename = "";
    fCurrentHitAttributeId = 0;
    fWriteToRootFlag = true;
    threadLocalData.Get().fBeginOfEventIndex = 0;
}

GateHitsCollection::~GateHitsCollection() {
}

size_t GateHitsCollection::GetBeginOfEventIndex() const {
    return threadLocalData.Get().fBeginOfEventIndex;
}

void GateHitsCollection::SetBeginOfEventIndex(size_t index) {
    threadLocalData.Get().fBeginOfEventIndex = index;
}

void GateHitsCollection::SetBeginOfEventIndex() {
    SetBeginOfEventIndex(GetSize());
}

void GateHitsCollection::SetWriteToRootFlag(bool f) {
    fWriteToRootFlag = f;
}

void GateHitsCollection::SetFilename(std::string filename) {
    fFilename = filename;
    if (fFilename.empty()) SetWriteToRootFlag(false);
    else SetWriteToRootFlag(true);
}

void GateHitsCollection::InitializeHitAttributes(const std::vector<std::string> &names) {
    StartInitialization();
    for (const auto &name: names)
        InitializeHitAttribute(name);
    FinishInitialization();
}

void GateHitsCollection::InitializeHitAttributes(const std::set<std::string> &names) {
    StartInitialization();
    for (const auto &name: names)
        InitializeHitAttribute(name);
    FinishInitialization();
}

void GateHitsCollection::StartInitialization() {
    if (!fWriteToRootFlag) return;
    auto *am = GateHitsCollectionsRootManager::GetInstance();
    auto id = am->DeclareNewTuple(fHitsCollectionName);
    fTupleId = id;
}

void GateHitsCollection::InitializeRootTupleForMaster() {
    if (!fWriteToRootFlag) return;
    auto *am = GateHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
}

void GateHitsCollection::InitializeRootTupleForWorker() {
    if (!fWriteToRootFlag) return;
    // no need if not multi-thread
    if (not G4Threading::IsMultithreadedApplication()) return;
    auto *am = GateHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
    SetBeginOfEventIndex();
}

void GateHitsCollection::FillToRootIfNeeded(bool clear) {
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

void GateHitsCollection::FillToRoot() {
    /*
     * maybe not very efficient to loop that way (row then column)
     * but I don't manage to do elsewhere
     */
    auto *am = GateHitsCollectionsRootManager::GetInstance();
    for (size_t i = 0; i < GetSize(); i++) {
        for (auto *att: fHitAttributes) {
            att->FillToRoot(i);
        }
        am->AddNtupleRow(fTupleId);
    }
    // required ! Cannot fill without clear
    Clear();
}

void GateHitsCollection::Clear() {
    for (auto *att: fHitAttributes) {
        att->Clear();
    }
    SetBeginOfEventIndex(0);
}

void GateHitsCollection::Write() const {
    if (!fWriteToRootFlag) return;
    auto *am = GateHitsCollectionsRootManager::GetInstance();
    am->Write(fTupleId);
}

void GateHitsCollection::Close() const {
    if (!fWriteToRootFlag) return;
    auto *am = GateHitsCollectionsRootManager::GetInstance();
    am->CloseFile(fTupleId);
}

void GateHitsCollection::InitializeHitAttribute(const std::string &name) {
    if (fHitAttributeMap.find(name) != fHitAttributeMap.end()) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' is already initialized. Abort";
        Fatal(oss.str());
    }
    auto *att = GateHitAttributeManager::GetInstance()->NewHitAttribute(name);
    InitializeHitAttribute(att);
}

void GateHitsCollection::InitializeHitAttribute(GateVHitAttribute* att) {
    auto name = att->GetHitAttributeName();
    if (fHitAttributeMap.find(name) != fHitAttributeMap.end()) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' is already initialized. Abort";
        Fatal(oss.str());
    }
    fHitAttributes.push_back(att);
    fHitAttributeMap[name] = att;
    att->SetHitAttributeId(fCurrentHitAttributeId);
    att->SetTupleId(fTupleId);
    fCurrentHitAttributeId++;
    // special case for type=3
    if (att->GetHitAttributeType() == '3')
        fCurrentHitAttributeId += 2;
}

void GateHitsCollection::FinishInitialization() {
    // Finally, not useful (yet?)
}

void GateHitsCollection::FillHits(G4Step *step) {
    for (auto *att: fHitAttributes) {
        att->ProcessHits(step);
    }
}

void GateHitsCollection::FillHitsWithEmptyValue() {
    for (auto *att: fHitAttributes) {
        att->FillHitWithEmptyValue();
    }
}

size_t GateHitsCollection::GetSize() const {
    if (fHitAttributes.empty()) return 0;
    return fHitAttributes[0]->GetSize();
}

GateVHitAttribute *GateHitsCollection::GetHitAttribute(const std::string &name) {
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

bool GateHitsCollection::IsHitAttributeExists(const std::string &name) const {
    return (fHitAttributeMap.count(name) != 0);
}


std::set<std::string> GateHitsCollection::GetHitAttributeNames() const {
    std::set<std::string> list;
    for (auto *att: fHitAttributes)
        list.insert(att->GetHitAttributeName());
    return list;
}

GateHitsCollection::Iterator GateHitsCollection::NewIterator() {
    return {this, 0};
}

std::string GateHitsCollection::DumpLastHit() const {
    std::ostringstream oss;
    int n = GetSize() - 1;
    for (auto *att: fHitAttributes) {
        oss << att->GetHitAttributeName() << " = " << att->Dump(n) << "  ";
    }
    return oss.str();
}
