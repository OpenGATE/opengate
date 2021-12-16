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


G4Mutex GamHitAttributeManagerMutex = G4MUTEX_INITIALIZER; // FIXME

GamHitAttributeManager *GamHitAttributeManager::fInstance = nullptr;

GamHitAttributeManager *GamHitAttributeManager::GetInstance() {
    if (fInstance == nullptr) fInstance = new GamHitAttributeManager();
    return fInstance;
}

GamHitAttributeManager::GamHitAttributeManager() {
    InitializeAllHitAttributes();
    //auto ram = G4RootAnalysisManager::Instance();
    //DDD(ram);
    //ram->SetNtupleMerging(true); // must be called before OpenFile
    //DDD("Set Merge on");
    fMergeFlagIsSet = false;
}

void GamHitAttributeManager::OpenFile(std::string filename) {
    //G4AutoLock mutex(&GamHitAttributeManagerMutex);
    // Warning : this pointer is not the same for all workers in MT mode
    auto ram = G4RootAnalysisManager::Instance();
    DDD(ram);
    if (not ram->IsOpenFile()) {
        // constexpr unsigned int kDefaultBasketSize = 32000;
        // constexpr unsigned int kDefaultBasketEntries = 4000;
        // FIXME: this is completely ignored ???
        // ram->SetBasketEntries(8000); // Does not seems to work
        // FIXME control nb of temporary write, but if too large, no output !?
        // ram->SetBasketSize(5e6);
        //ram->SetNtupleRowWise(false, false); // ????

        // How to prevent warning ???

        ram->SetNtupleMerging(true); // must be called before OpenFile /// needed here
        fMergeFlagIsSet = true;
        DDD("OpenFile");
        ram->OpenFile(filename);
        // FIXME if several HC Actor, already open : warning
    } else {
        auto fn = ram->GetFileName();
        DD(fn);
        if (fn != G4String(filename)) {
            std::ostringstream oss;
            oss << "Error, only ONE single root output is allowed. This HitsCollection output is '"
                << filename << "' while the previous one was '" << fn << "'. ";
            Fatal(oss.str());
        }
    }
}

/*
void GamHitAttributeManager::InsertTupleId(int tupleId) {
    DDD("InsertTupleId")
    DDD(tupleId);
    fTupleIdSet.insert(tupleId);
}
 */

int GamHitAttributeManager::DeclareNewTuple(std::string name) {
    DDD("DeclareNewTuple");
    DDD(name);
    int id = -1;
    for (auto m:fTupleNameIdMap) {
        DDD(m.first);
        DDD(m.second);
        if (m.first == name) {
            DDD("found");
            return m.second;
        }
        id = std::max(id, m.second);
    }
    DDD(id);
    id += 1;
    fTupleNameIdMap[name] = id;
    DDD(fTupleNameIdMap[name]);
    return id;
}

void GamHitAttributeManager::CreateRootTuple(std::shared_ptr<GamHitsCollection> hc) {
    G4AutoLock mutex(&GamHitAttributeManagerMutex);
    DDD("CreateRootTuple");
    auto ram = G4RootAnalysisManager::Instance();
    ram->SetVerboseLevel(0);
    OpenFile(hc->GetFilename());
    auto id = ram->CreateNtuple(hc->GetName(), hc->GetTitle());
    DDD(id);
    assert(id == hc->fRootTupleId);

    for (auto att: hc->fHitAttributes) {
        // FIXME depends on the type -> todo in the HitAttribute ?
        auto att_id = ram->CreateNtupleDColumn(id, att->fHitAttributeName);
        DDD(att_id);
        att->fHitAttributeId = att_id;
    }

    ram->FinishNtuple(id);
    DDD("finish n tuple");
}


void GamHitAttributeManager::CloseFile(int tupleId) {
    G4AutoLock mutex(&GamHitAttributeManagerMutex);
    DDD("Close ? ");
    DDD(tupleId);
    fTupleIdSet.erase(tupleId);
    if (fTupleIdSet.empty()) {
        DDD("CLOSE");
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
    DDD(att->fHitAttributeName);
    if (att->fHitAttributeType == 'D') {
        auto a = new GamTHitAttribute<double>(att->fHitAttributeName);
        a->fProcessHitsFunction = att->fProcessHitsFunction;
        return a;
    }
    Fatal("Error in CopyHitAttribute"); // FIXME
    return nullptr;
}




