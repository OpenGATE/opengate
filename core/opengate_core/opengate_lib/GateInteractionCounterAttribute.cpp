/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateInteractionCounterAttribute.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"
#include <G4VProcess.hh>

GateInteractionCounterAttribute::GateInteractionCounterAttribute(
    py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fDigiAttributeType = 'I';
  fActions.insert("SteppingAction");
}

void GateInteractionCounterAttribute::InitializeUserInfo(py::dict &user_info) {
  GateVAuxiliaryAttribute::InitializeUserInfo(user_info);
  fProcessName = DictGetStr(user_info, "process_name");
  fPropagateFromParentTrack =
      DictGetBool(user_info, "propagate_from_parent_track");
}

void GateInteractionCounterAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();

  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    att->FillIValue(GetIValue(step));
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

int GateInteractionCounterAttribute::GetIValue(const G4Step *step) const {
  return GetAuxiliaryTrackInformationValue<
      GateIntegerCounterAuxiliaryTrackInformation, int>(
      step, 0, &GateIntegerCounterAuxiliaryTrackInformation::GetCount);
}

void GateInteractionCounterAttribute::SteppingAction(const G4Step *step) {
  const auto *process = step->GetPreStepPoint()->GetProcessDefinedStep();
  if (process != nullptr && process->GetProcessName() == fProcessName) {
    auto *info = GetOrCreateAuxiliaryTrackInformation<
        GateIntegerCounterAuxiliaryTrackInformation>(step->GetTrack());
    info->Increment();
  }
  if (fPropagateFromParentTrack) {
    PropagateAuxiliaryTrackInformationToSecondariesInCurrentStep<
        GateIntegerCounterAuxiliaryTrackInformation>(step);
  }
}
