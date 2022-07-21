/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamActorManager.h"
#include "GamHelpers.h"

GamActorManager *GamActorManager::fInstance = nullptr;
std::vector<GamVActor *> GamActorManager::fActors;

GamActorManager *GamActorManager::GetInstance() {
    if (GamActorManager::fInstance == nullptr)
        GamActorManager::fInstance = new GamActorManager;
    return GamActorManager::fInstance;
}

GamActorManager::~GamActorManager() {
}

void GamActorManager::AddActor(GamVActor *actor) {
    for (auto *a: fActors) {
        if (a->GetName() == actor->GetName()) {
            std::ostringstream oss;
            oss << "Cannot add the actor '" << actor->GetName()
                << "' because another actor with the same name already exists";
            Fatal(oss.str());
        }
    }
    fActors.push_back(actor);
}

GamVActor *GamActorManager::GetActor(std::string name) {
    for (auto *a: fActors) {
        if (a->GetName() == name) return a;
    }
    std::ostringstream oss;
    oss << "Cannot get the actor '" << name
        << "' because it does not exists in the list: ";
    for (auto *a: fActors)
        oss << a->GetName() << " ";
    Fatal(oss.str());
    return nullptr;
}
