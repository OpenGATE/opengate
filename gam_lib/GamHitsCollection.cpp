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


GamHitsCollection::GamHitsCollection(std::string collName) :
    G4VHitsCollection("", collName), fHitsCollectionName(collName) {
    fTupleId = -1;
    fHitsCollectionTitle = "Hits collection";
    fFilename = "";
    fCurrentHitAttributeId = 0;
    fWriteToRootFlag = true;
}

GamHitsCollection::~GamHitsCollection() {
}


void GamHitsCollection::SetWriteToRootFlag(bool f) {
    fWriteToRootFlag = f;
}

void GamHitsCollection::SetFilename(std::string filename) {
    fFilename = filename;
    if (fFilename == "") SetWriteToRootFlag(false);
    else SetWriteToRootFlag(true);
}

void GamHitsCollection::InitializeHitAttributes(const std::vector<std::string> &names) {
    StartInitialization();
    for (auto &name: names)
        InitializeHitAttribute(name);
    FinishInitialization();
}

void GamHitsCollection::InitializeHitAttributes(const std::set<std::string> &names) {
    StartInitialization();
    for (auto &name: names)
        InitializeHitAttribute(name);
    FinishInitialization();
}

void GamHitsCollection::StartInitialization() {
    if (!fWriteToRootFlag) return;
    auto am = GamHitsCollectionsRootManager::GetInstance();
    auto id = am->DeclareNewTuple(fHitsCollectionName);
    fTupleId = id;
}

void GamHitsCollection::InitializeRootTupleForMaster() {
    if (!fWriteToRootFlag) return;
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
}

void GamHitsCollection::InitializeRootTupleForWorker() {
    if (!fWriteToRootFlag) return;
    // no need if not multi-thread
    if (not G4Threading::IsMultithreadedApplication()) return;
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->CreateRootTuple(this);
}

void GamHitsCollection::FillToRoot(bool clear) {
    if (!fWriteToRootFlag) return;
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
    if (clear) Clear();
}

void GamHitsCollection::Clear() {
    for (auto att: fHitAttributes) {
        att->Clear();
    }
}

void GamHitsCollection::Write() {
    if (!fWriteToRootFlag) return;
    auto am = GamHitsCollectionsRootManager::GetInstance();
    am->Write(fTupleId);
}

void GamHitsCollection::Close() {
    if (!fWriteToRootFlag) return;
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
    // Finally, not useful (yet?)
}

void GamHitsCollection::ProcessHits(G4Step *step, G4TouchableHistory *touchable) {
    for (auto att: fHitAttributes) {
        att->ProcessHits(step, touchable);
    }
}

size_t GamHitsCollection::GetSize() const {
    if (fHitAttributes.empty()) return 0;
    return fHitAttributes[0]->GetSize();
}

GamVHitAttribute *GamHitsCollection::GetHitAttribute(const std::string &name) {
    /*if (not IsHitAttributeExists(name)) {
        std::ostringstream oss;
        oss << "Error the branch named '" << name << "' does not exist. Abort";
        Fatal(oss.str());
    }
    return fHitAttributeMap[name];
     */
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
