/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateActorManager.h"
#include "GateHelpers.h"

GateActorManager *GateActorManager::fInstance = nullptr;
std::vector<GateVActor *> GateActorManager::fActors;

GateActorManager *GateActorManager::GetInstance() {
  if (GateActorManager::fInstance == nullptr)
    GateActorManager::fInstance = new GateActorManager;
  return GateActorManager::fInstance;
}

GateActorManager::~GateActorManager() = default;

void GateActorManager::AddActor(GateVActor *actor) {
  for (auto *a : fActors) {
    if (a->GetName() == actor->GetName()) {
      std::ostringstream oss;
      oss << "Cannot add the actor '" << actor->GetName()
          << "' because another actor with the same name already exists";
      Fatal(oss.str());
    }
  }
  fActors.push_back(actor);
}

GateVActor *GateActorManager::GetActor(std::string name) {
  for (auto *a : fActors) {
    if (a->GetName() == name)
      return a;
  }
  std::ostringstream oss;
  oss << "Cannot get the actor '" << name
      << "' because it does not exists in the list: ";
  for (auto *a : fActors)
    oss << a->GetName() << " ";
  Fatal(oss.str());
  return nullptr;
}
