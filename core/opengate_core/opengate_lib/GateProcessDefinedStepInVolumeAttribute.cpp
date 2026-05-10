/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateProcessDefinedStepInVolumeAttribute.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"
#include <G4StepPoint.hh>
#include <G4VPhysicalVolume.hh>
#include <G4VProcess.hh>

GateProcessDefinedStepInVolumeAttribute::GateProcessDefinedStepInVolumeAttribute(
    py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fDigiAttributeType = 'I';
  fActions.insert("SteppingAction");
}

void GateProcessDefinedStepInVolumeAttribute::InitializeUserInfo(
    py::dict &user_info) {
  GateVAuxiliaryAttribute::InitializeUserInfo(user_info);
  fProcessName = DictGetStr(user_info, "process_name");
  fVolumeName = DictGetStr(user_info, "volume_name");
  fPropagateFromParentTrack = DictGetBool(user_info, "propagate_from_parent_track");
}

void GateProcessDefinedStepInVolumeAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();

  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    att->FillIValue(GetAuxiliaryTrackInformationValue<
                    GateIntegerCounterAuxiliaryTrackInformation, int>(
        step, 0, &GateIntegerCounterAuxiliaryTrackInformation::GetCount));
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

void GateProcessDefinedStepInVolumeAttribute::SteppingAction(
    const G4Step *step) {
  const auto *pre_step_point = step->GetPreStepPoint();
  const auto &touchable = pre_step_point->GetTouchableHandle();
  bool in_configured_volume = false;
  const auto history_depth = touchable->GetHistoryDepth();
  for (int depth = 0; depth <= history_depth; depth++) {
    const auto *physical_volume = touchable->GetVolume(depth);
    if (physical_volume != nullptr &&
        physical_volume->GetLogicalVolume()->GetName() == fVolumeName) {
      in_configured_volume = true;
      break;
    }
  }

  if (in_configured_volume) {
    const auto *process = pre_step_point->GetProcessDefinedStep();
    if (process != nullptr && process->GetProcessName() == fProcessName) {
      auto *info = GetOrCreateAuxiliaryTrackInformation<
          GateIntegerCounterAuxiliaryTrackInformation>(step->GetTrack());
      info->Increment();
    }
  }

  if (fPropagateFromParentTrack) {
    PropagateAuxiliaryTrackInformationToSecondariesInCurrentStep<
        GateIntegerCounterAuxiliaryTrackInformation>(step);
  }
}
