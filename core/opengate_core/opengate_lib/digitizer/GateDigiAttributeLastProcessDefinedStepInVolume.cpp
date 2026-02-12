/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAttributeLastProcessDefinedStepInVolume.h"
#include "../GateActorManager.h"
#include "../GateHelpers.h"
#include "../GateUniqueVolumeID.h"
#include "GateDigiAttributeManager.h"
#include "GateTDigiAttribute.h"
#include <G4RunManager.hh>

GateDigiAttributeLastProcessDefinedStepInVolume::
    GateDigiAttributeLastProcessDefinedStepInVolume(
        const std::string &att_name,
        const GateDigiAttributeLastProcessDefinedStepInVolumeActor *actor)
    : GateTDigiAttribute<std::string>(att_name) {
  // create the lambda function that will be called each step
  auto l = [=](GateVDigiAttribute *att, G4Step *step) {
    // we CANNOT use att here (it is a different copy without fActor)
    const auto i = this->GetProcessDefinedStepInVolume(step);
    att->FillSValue(i);
  };

  // define a new attribute
  auto *m = GateDigiAttributeManager::GetInstance();
  m->DefineDigiAttribute(att_name, 'S', l);

  // Set the linked actor
  fActor = actor;
}

std::string GateDigiAttributeLastProcessDefinedStepInVolume::GetProcessDefinedStepInVolume(
    const G4Step *step) const {
  // retrieve the nb stored in the att
  const std::string n = fActor->GetLastProcess();
  return n;
}
