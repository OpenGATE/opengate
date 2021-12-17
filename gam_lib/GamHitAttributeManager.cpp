/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitAttributeManager.h"
#include "GamTHitAttribute.h"

GamHitAttributeManager *GamHitAttributeManager::fInstance = nullptr;

GamHitAttributeManager *GamHitAttributeManager::GetInstance() {
    if (fInstance == nullptr) fInstance = new GamHitAttributeManager();
    return fInstance;
}

GamHitAttributeManager::GamHitAttributeManager() {
    InitializeAllHitAttributes();
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




