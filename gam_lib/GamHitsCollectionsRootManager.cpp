/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitsCollectionsRootManager.h"
#include "G4RootAnalysisManager.hh"
#include "G4RunManager.hh"
#include "G4Run.hh"

GamHitsCollectionsRootManager *GamHitsCollectionsRootManager::fInstance = nullptr;

GamHitsCollectionsRootManager *GamHitsCollectionsRootManager::GetInstance() {
    if (fInstance == nullptr) fInstance = new GamHitsCollectionsRootManager();
    return fInstance;
}

GamHitsCollectionsRootManager::GamHitsCollectionsRootManager() {
}

void GamHitsCollectionsRootManager::OpenFile(int tupleId, std::string filename) {
    // Warning : this pointer is not the same for all workers in MT mode
    auto ram = G4RootAnalysisManager::Instance();
    if (not ram->IsOpenFile()) {
        // The following does not seems to work (default is 4000)
        // ram->SetBasketEntries(8000);
        // ram->SetBasketSize(5e6);

        // SetNtupleMerging must be called before OpenFile
        // To avoid a warning, the flag is only set for the master thread
        // and for the first opened tuple only.
        if (G4Threading::IsMultithreadedApplication()) {
            auto run = G4RunManager::GetRunManager()->GetCurrentRun();
            if (run) {
                if (run->GetRunID() == 0 and tupleId == 0)
                    ram->SetNtupleMerging(true);
            } else ram->SetNtupleMerging(true);
        }
        ram->OpenFile(filename);
    }
}

int GamHitsCollectionsRootManager::DeclareNewTuple(std::string name) {
    if (fTupleNameIdMap.count(name) != 0) {
        std::ostringstream oss;
        oss << "Error cannot create a tuple named '" << name
            << "' because it already exists. ";
        Fatal(oss.str());
    }
    int id = -1;
    for (const auto &m: fTupleNameIdMap) {
        if (m.first == name) {
            DDD("tuple already declared");
            DDD(m.second);
            DDD(name);
            return m.second;
        }
        id = std::max(id, m.second);
    }
    id += 1;
    fTupleNameIdMap[name] = id;
    return id;
}

void GamHitsCollectionsRootManager::AddNtupleRow(int tupleId) {
    auto ram = G4RootAnalysisManager::Instance();
    ram->AddNtupleRow(tupleId);
}

void GamHitsCollectionsRootManager::Write() {
    auto ram = G4RootAnalysisManager::Instance();
    ram->Write();
}

void GamHitsCollectionsRootManager::CreateRootTuple(const GamHitsCollection *hc) {
    auto ram = G4RootAnalysisManager::Instance();
    // Later, the verbosity could be an option
    ram->SetVerboseLevel(0);
    OpenFile(hc->GetTupleId(), hc->GetFilename());
    auto id = ram->CreateNtuple(hc->GetName(), hc->GetTitle());
    // Important ! This allows to write to several root files
    ram->SetNtupleFileName(hc->GetTupleId(), hc->GetFilename());
    for (auto att: hc->GetHitAttributes()) {
        // FIXME depends on the type -> todo in the HitAttribute ?
        // WARNING: the id can be different from tupleId in HC and in att
        // because it is created at all runs (mandatory).
        // So id must be used to create columns, not tupleID in att.
        CreateNtupleColumn(id, att);
    }
    ram->FinishNtuple(id);
}

void GamHitsCollectionsRootManager::CreateNtupleColumn(int tupleId, GamVHitAttribute *att) {
    auto ram = G4RootAnalysisManager::Instance();
    int att_id = -1;
    if (att->fHitAttributeType == 'D')
        att_id = ram->CreateNtupleDColumn(tupleId, att->fHitAttributeName);
    // FIXME other types + check
    if (att_id == -1) {
        Fatal("Error CreateNtupleColumn");
    }
    att->fHitAttributeId = att_id;
}

void GamHitsCollectionsRootManager::CloseFile(int tupleId) {
    // find the tuple and remove it from the map
    for (auto iter = fTupleNameIdMap.begin(); iter != fTupleNameIdMap.end();) {
        if (iter->second == tupleId) {
            fTupleNameIdMap.erase(iter++);
        } else ++iter;
    }
    // close only when the last tuple is done
    if (fTupleNameIdMap.size() == 0) {
        auto ram = G4RootAnalysisManager::Instance();
        ram->CloseFile();
    }
}

