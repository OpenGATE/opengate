/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateLastInteractionPositionInVolumeAttribute.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"
#include <limits>
#include <G4StepPoint.hh>
#include <G4VPhysicalVolume.hh>
#include <G4VProcess.hh>

GateLastInteractionPositionInVolumeAttribute::
    GateLastInteractionPositionInVolumeAttribute(py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fDigiAttributeType = '3';
  fActions.insert("SteppingAction");
}

void GateLastInteractionPositionInVolumeAttribute::InitializeUserInfo(
    py::dict &user_info) {
  GateVAuxiliaryAttribute::InitializeUserInfo(user_info);
  fVolumeName = DictGetStr(user_info, "volume_name");
  fPropagateFromParentTrack =
      DictGetBool(user_info, "propagate_from_parent_track");
}

void GateLastInteractionPositionInVolumeAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();

  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    att->Fill3Value(Get3Value(step));
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

G4ThreeVector GateLastInteractionPositionInVolumeAttribute::Get3Value(
    const G4Step *step) const {
  // Use NaN as the public "unset" sentinel so analysis code can distinguish
  // "no qualifying interaction seen yet" from a real interaction at (0, 0, 0).
  const auto nan = std::numeric_limits<double>::quiet_NaN();
  return GetStoredTrackDataValue<GateThreeVectorTrackData, G4ThreeVector>(
      step, G4ThreeVector(nan, nan, nan));
}

void GateLastInteractionPositionInVolumeAttribute::SteppingAction(
    const G4Step *step) {
  const auto *pre_step_point = step->GetPreStepPoint();
  if (IsStepInVolume(step, fVolumeName)) {
    const auto *process = pre_step_point->GetProcessDefinedStep();
    if (process != nullptr && process->GetProcessName() != "Transportation") {
      SetStoredTrackDataValue<GateThreeVectorTrackData, G4ThreeVector>(
          step->GetTrack(), pre_step_point->GetPosition());
    }
  }

  if (fPropagateFromParentTrack) {
    PropagateTrackDataToSecondariesInCurrentStep<GateThreeVectorTrackData>(
        step);
  }
}
