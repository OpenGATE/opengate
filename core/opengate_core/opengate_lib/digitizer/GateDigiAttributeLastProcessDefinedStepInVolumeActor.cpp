/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAttributeLastProcessDefinedStepInVolumeActor.h"
#include "GateDigiAttributeLastProcessDefinedStepInVolume.h"
#include <G4RunManager.hh>
#include <G4VProcess.hh>

GateDigiAttributeLastProcessDefinedStepInVolumeActor::
    GateDigiAttributeLastProcessDefinedStepInVolumeActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("BeginOfEventAction");
  fActions.insert("SteppingAction");
}

void GateDigiAttributeLastProcessDefinedStepInVolumeActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fAttribute =
      new GateDigiAttributeLastProcessDefinedStepInVolume(GetName(), this);
}

void GateDigiAttributeLastProcessDefinedStepInVolumeActor::BeginOfEventAction(
    const G4Event *event) {
  fThreadLocalData.Get().fLastProcess = "Transportation";
}

std::string
GateDigiAttributeLastProcessDefinedStepInVolumeActor::GetLastProcess() const {
  return fThreadLocalData.Get().fLastProcess;
}

void GateDigiAttributeLastProcessDefinedStepInVolumeActor::SteppingAction(
    G4Step *step) {
  // check the process-defined step
  const auto *p = step->GetPreStepPoint()->GetProcessDefinedStep();
  if (p == nullptr)
    return;
  // Store the interaction
  if (p->GetProcessName() != "Transportation") {
    fThreadLocalData.Get().fLastProcess = p->GetProcessName();
  }
}
