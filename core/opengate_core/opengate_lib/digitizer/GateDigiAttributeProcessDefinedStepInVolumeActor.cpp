/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAttributeProcessDefinedStepInVolumeActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiAttributeProcessDefinedStepInVolume.h"
#include <G4RunManager.hh>
#include <G4VProcess.hh>

GateDigiAttributeProcessDefinedStepInVolumeActor::
    GateDigiAttributeProcessDefinedStepInVolumeActor(py::dict &user_info)
    : GateVActor(user_info, false) {
  fActions.insert("BeginOfEventAction");
  fActions.insert("SteppingAction");
}

void GateDigiAttributeProcessDefinedStepInVolumeActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fProcessName = DictGetStr(user_info, "process_name");
  fAttribute = new GateDigiAttributeProcessDefinedStepInVolume(GetName(), this);
}

void GateDigiAttributeProcessDefinedStepInVolumeActor::BeginOfEventAction(
    const G4Event *event) {
  fNumberOfInteractions = 0;
}

int GateDigiAttributeProcessDefinedStepInVolumeActor::GetNumberOfInteractions()
    const {
  return fNumberOfInteractions;
}

void GateDigiAttributeProcessDefinedStepInVolumeActor::SteppingAction(
    G4Step *step) {
  // check the process-defined step
  const auto *p = step->GetPreStepPoint()->GetProcessDefinedStep();
  if (p == nullptr)
    return;
  // Store the interaction
  if (p->GetProcessName() == fProcessName) {
    fNumberOfInteractions++;
  }
}
