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

GateProcessDefinedStepInVolumeAttribute::
    GateProcessDefinedStepInVolumeAttribute(py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fDigiAttributeType = 'I';
  fActions.insert("SteppingAction");
}

void GateProcessDefinedStepInVolumeAttribute::InitializeUserInfo(
    py::dict &user_info) {
  GateVAuxiliaryAttribute::InitializeUserInfo(user_info);
  fProcessName = DictGetStr(user_info, "process_name");
  py::object volume_name_obj = user_info["volume_names"];
  if (py::isinstance<py::str>(volume_name_obj)) {
    fVolumeNameList.push_back(DictGetStr(user_info, "volume_names"));
  } else {
    fVolumeNameList = DictGetVecStr(user_info, "volume_names");
  }
  fPropagateFromParentTrack =
      DictGetBool(user_info, "propagate_from_parent_track");
}

void GateProcessDefinedStepInVolumeAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();

  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    att->FillIValue(GetIValue(step));
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

int GateProcessDefinedStepInVolumeAttribute::GetIValue(
    const G4Step *step) const {
  return GetTrackDataValue<GateIntegerCounterTrackData, int>(
      step, 0, &GateIntegerCounterTrackData::GetCount);
}

void GateProcessDefinedStepInVolumeAttribute::SteppingAction(
    const G4Step *step) {
  const auto *pre_step_point = step->GetPreStepPoint();
  for (const auto &volumeName : fVolumeNameList) {
    if (IsStepInVolume(step, volumeName)) {
      const auto *process = pre_step_point->GetProcessDefinedStep();
      if (process != nullptr && process->GetProcessName() == fProcessName) {
        auto *info =
            GetOrCreateTrackData<GateIntegerCounterTrackData>(step->GetTrack());
        info->Increment();
      }
    }
  }

  if (fPropagateFromParentTrack) {
    PropagateTrackDataToSecondariesInCurrentStep<GateIntegerCounterTrackData>(
        step);
  }
}
