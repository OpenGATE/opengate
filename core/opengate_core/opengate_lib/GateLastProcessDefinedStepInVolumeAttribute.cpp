/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateLastProcessDefinedStepInVolumeAttribute.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"
#include <G4StepPoint.hh>
#include <G4VPhysicalVolume.hh>
#include <G4VProcess.hh>

GateLastProcessDefinedStepInVolumeAttribute::
    GateLastProcessDefinedStepInVolumeAttribute(py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fDigiAttributeType = 'S';
  fActions.insert("SteppingAction");
}

void GateLastProcessDefinedStepInVolumeAttribute::InitializeUserInfo(
    py::dict &user_info) {
  GateVAuxiliaryAttribute::InitializeUserInfo(user_info);
  fVolumeName = DictGetStr(user_info, "volume_name");
  fPropagateFromParentTrack =
      DictGetBool(user_info, "propagate_from_parent_track");
}

void GateLastProcessDefinedStepInVolumeAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();

  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    att->FillSValue(GetSValue(step));
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

std::string GateLastProcessDefinedStepInVolumeAttribute::GetSValue(
    const G4Step *step) const {
  return GetAuxiliaryTrackInformationStoredValue<
      GateStringAuxiliaryTrackInformation, std::string>(step, "Transportation");
}

void GateLastProcessDefinedStepInVolumeAttribute::SteppingAction(
    const G4Step *step) {
  const auto *pre_step_point = step->GetPreStepPoint();
  if (IsStepInVolume(step, fVolumeName)) {
    const auto *process = pre_step_point->GetProcessDefinedStep();
    if (process != nullptr && process->GetProcessName() != "Transportation") {
      SetAuxiliaryTrackInformationStoredValue<
          GateStringAuxiliaryTrackInformation, std::string>(
          step->GetTrack(), process->GetProcessName());
    }
  }

  if (fPropagateFromParentTrack) {
    PropagateAuxiliaryTrackInformationToSecondariesInCurrentStep<
        GateStringAuxiliaryTrackInformation>(step);
  }
}
