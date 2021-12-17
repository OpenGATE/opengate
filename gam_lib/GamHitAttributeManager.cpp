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
        oss << branch.second->GetHitAttributeName() << " ";
    return oss.str();
}

void GamHitAttributeManager::DefineHitAttribute(std::string name, char type,
                                                const GamVHitAttribute::ProcessHitsFunctionType & f) {
    GamVHitAttribute *att = nullptr;
    if (type == 'D') att = new GamTHitAttribute<double>(name);
    if (type == 'I') att = new GamTHitAttribute<int>(name);
    if (type == 'S') att = new GamTHitAttribute<std::string>(name);
    if (type == '3') att = new GamTHitAttribute<G4ThreeVector>(name);
    if (att == nullptr) {
        std::ostringstream oss;
        oss << "Error while defining HitAttribute " << name
            << " the type '" << type << "' is unknown.";
        Fatal(oss.str());
    } else {
        att->fProcessHitsFunction = std::move(f);
        fAvailableHitAttributes[att->GetHitAttributeName()] = att;
    }
}


GamVHitAttribute *GamHitAttributeManager::CopyHitAttribute(GamVHitAttribute *att) {
    GamVHitAttribute *a = nullptr;
    if (att->GetHitAttributeType() == 'D') {
        a = new GamTHitAttribute<double>(att->GetHitAttributeName());
    }
    if (att->GetHitAttributeType() == 'I') {
        a = new GamTHitAttribute<int>(att->GetHitAttributeName());
    }
    if (att->GetHitAttributeType() == 'S') {
        a = new GamTHitAttribute<std::string>(att->GetHitAttributeName());
    }
    if (att->GetHitAttributeType() == '3') {
        a = new GamTHitAttribute<G4ThreeVector>(att->GetHitAttributeName());
    }
    if (a != nullptr) {
        a->fProcessHitsFunction = att->fProcessHitsFunction;
        return a;
    }
    DDD(att->GetHitAttributeName());
    DDD(att->GetHitAttributeType());
    DDD(att->GetHitAttributeTupleId());
    Fatal("Error in CopyHitAttribute"); // FIXME
    return nullptr;
}




