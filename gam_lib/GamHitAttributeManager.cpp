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

GamHitAttributeManager *GamHitAttributeManager::fInstance = nullptr;

GamHitAttributeManager *GamHitAttributeManager::GetInstance() {
    if (fInstance == nullptr) fInstance = new GamHitAttributeManager();
    return fInstance;
}

GamHitAttributeManager::GamHitAttributeManager() {
    InitializeAllHitAttributes();

}

void GamHitAttributeManager::OpenFile(std::string filename) {
    auto ram = G4RootAnalysisManager::Instance();
    if (not ram->IsOpenFile()) {
        // constexpr unsigned int kDefaultBasketSize = 32000;
        // constexpr unsigned int kDefaultBasketEntries = 4000;
        // FIXME: this is completely ignored ???
        // ram->SetBasketEntries(8000); // Does not seems to work
        // FIXME control nb of temporary write, but if too large, no output !?
        // ram->SetBasketSize(5e6);
        //ram->SetNtupleRowWise(false, false); // ????
        ram->SetNtupleMerging(true); // must be called before OpenFile
        DDD("OpenFile");
        ram->OpenFile(filename);
    } else {
        auto fn = ram->GetFileName();
        DD(fn);
        if (fn != filename) {
            std::ostringstream oss;
            oss << "Error, only ONE single root output is allowed. This HitsCollection output is '"
                << filename << "' while the previous one was '" << fn << "'. ";
            Fatal(oss.str());
        }
    }
}

void GamHitAttributeManager::AddTupleId(int tupleId) {
    DDD("AddTupleId")
    DDD(tupleId);
    fTupleIdSet.insert(tupleId);
}

void GamHitAttributeManager::CloseFile(int tupleId) {
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




