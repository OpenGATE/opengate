/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAttributeProcessDefinedStepInVolume.h"
#include "../GateActorManager.h"
#include "../GateHelpers.h"
#include "../GateUniqueVolumeID.h"
#include "GateDigiAttributeManager.h"
#include "GateTDigiAttribute.h"
#include <G4RunManager.hh>

GateDigiAttributeProcessDefinedStepInVolume::
    GateDigiAttributeProcessDefinedStepInVolume(
        const std::string &att_name,
        const GateDigiAttributeProcessDefinedStepInVolumeActor *actor)
    : GateTDigiAttribute<int>(att_name) {
  // create the lambda function that will be called each step
  auto l = [=](GateVDigiAttribute *att, G4Step *step) {
    // we CANNOT use att here (it is a different copy without fActor)
    const auto i = this->GetProcessDefinedStepInVolume(step);
    att->FillIValue(i);
  };

  // define a new attribute
  auto *m = GateDigiAttributeManager::GetInstance();
  m->DefineDigiAttribute(att_name, 'I', l);

  // Set the linked actor
  fActor = actor;
}

int GateDigiAttributeProcessDefinedStepInVolume::GetProcessDefinedStepInVolume(
    const G4Step *step) const {
  // retrieve the nb stored in the att
  const int n = fActor->GetNumberOfInteractions();
  return n;
}
