/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitAttributeManager.h"
#include "GamVHitAttribute.h"
#include "GamTHitAttribute.h"
#include "G4Step.hh"

G4Mutex GamHitAttributeManagerMutex = G4MUTEX_INITIALIZER;

GamHitAttributeManager *GamHitAttributeManager::fInstance = nullptr;

GamHitAttributeManager *GamHitAttributeManager::GetInstance() {
    if (fInstance == nullptr) fInstance = new GamHitAttributeManager();
    return fInstance;
}

GamHitAttributeManager::GamHitAttributeManager() {
    InitializeAllHitAttributes();
}

void GamHitAttributeManager::OpenFile(int tupleId, std::string filename) {
    // Warning : this pointer is not the same for all workers in MT mode
    auto ram = G4RootAnalysisManager::Instance();
    if (not ram->IsOpenFile()) {
        // The following does not seems to work (default is 4000)
        // ram->SetBasketEntries(8000);
        // ram->SetBasketSize(5e6);

        // SetNtupleMerging must be called before OpenFile
        // To avoid a warning, the flag is only set for the master thread
        // and for the first opened tuple only.
        auto run = G4RunManager::GetRunManager()->GetCurrentRun();
        if (run) {
            if (run->GetRunID() == 0 and tupleId == 0)
                ram->SetNtupleMerging(true);
        } else ram->SetNtupleMerging(true);
        ram->OpenFile(filename);
    }
}

int GamHitAttributeManager::DeclareNewTuple(std::string name) {
    DDD("DeclareNewTuple");
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
    return id;
}

void GamHitAttributeManager::AddNtupleRow(int tupleId) {
    auto ram = G4RootAnalysisManager::Instance();
    ram->AddNtupleRow(tupleId);
}

void GamHitAttributeManager::Write() {
    auto ram = G4RootAnalysisManager::Instance();
    ram->Write();
}

void GamHitAttributeManager::CreateRootTuple(std::shared_ptr<GamHitsCollection> hc) {
    G4AutoLock mutex(&GamHitAttributeManagerMutex);
    auto ram = G4RootAnalysisManager::Instance();
    // Later, the verbosity could be an option
    ram->SetVerboseLevel(0);
    OpenFile(hc->GetTupleId(), hc->GetFilename());
    auto id = ram->CreateNtuple(hc->GetName(), hc->GetTitle());
    // Important ! This allows to write to several root files
    ram->SetNtupleFileName(hc->GetTupleId(), hc->GetFilename());
    for (auto att: hc->GetHitAttributes()) {
        // FIXME depends on the type -> todo in the HitAttribute ?
        auto att_id = ram->CreateNtupleDColumn(id, att->fHitAttributeName);
        att->fHitAttributeId = att_id;
    }
    ram->FinishNtuple(id);
}

void GamHitAttributeManager::CloseFile(int tupleId) {
    G4AutoLock mutex(&GamHitAttributeManagerMutex);
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

GamVHitAttribute *GamHitAttributeManager::NewHitAttribute(std::string name) {
    if (fAvailableHitAttributes.find(name) == fAvailableHitAttributes.end()) {
        DDD("ERROR");
        std::ostringstream oss;
        oss << "Error the attribute named '" << name << "' does not exists. Abort";
        oss << " List of available attributes : " << DumpAvailableHitAttributeNames();
        Fatal(oss.str());
    }
    return CopyHitAttribute(fAvailableHitAttributes[name]);
}


std::string GamHitAttributeManager::DumpAvailableHitAttributeNames() {
    std::ostringstream oss;
    for (const auto &branch: fAvailableHitAttributes)
        oss << branch.second->fHitAttributeName << " ";
    return oss.str();
}

void GamHitAttributeManager::InitializeAllHitAttributes() {
    DDD("First time here, GamHitAttributeManager initialization");
    auto b = new GamTHitAttribute<double>("TotalEnergyDeposit");
    b->fProcessHitsFunction =
        [=](GamVHitAttribute *branch, G4Step *step, G4TouchableHistory *) {
            //branch->push_back_double(step->GetPostStepPoint()->GetKineticEnergy());
            //DDD(step->GetTotalEnergyDeposit());
            branch->FillDValue(step->GetTotalEnergyDeposit());
        };
    fAvailableHitAttributes[b->fHitAttributeName] = b;
}

GamVHitAttribute *GamHitAttributeManager::CopyHitAttribute(GamVHitAttribute *att) {
    if (att->fHitAttributeType == 'D') {
        auto a = new GamTHitAttribute<double>(att->fHitAttributeName);
        a->fProcessHitsFunction = att->fProcessHitsFunction;
        return a;
    }
    Fatal("Error in CopyHitAttribute"); // FIXME
    return nullptr;
}




