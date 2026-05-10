/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateLastInteractionPositionInVolumeAttribute.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"
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

G4ThreeVector
GateLastInteractionPositionInVolumeAttribute::Get3Value(
    const G4Step *step) const {
  return GetAuxiliaryTrackInformationStoredValue<
      GateThreeVectorAuxiliaryTrackInformation, G4ThreeVector>(
      step, G4ThreeVector());
}

void GateLastInteractionPositionInVolumeAttribute::SteppingAction(
    const G4Step *step) {
  const auto *pre_step_point = step->GetPreStepPoint();
  if (IsStepInVolume(step, fVolumeName)) {
    const auto *process = pre_step_point->GetProcessDefinedStep();
    if (process != nullptr && process->GetProcessName() != "Transportation") {
      SetAuxiliaryTrackInformationStoredValue<
          GateThreeVectorAuxiliaryTrackInformation, G4ThreeVector>(
          step->GetTrack(), pre_step_point->GetPosition());
    }
  }

  if (fPropagateFromParentTrack) {
    PropagateAuxiliaryTrackInformationToSecondariesInCurrentStep<
        GateThreeVectorAuxiliaryTrackInformation>(step);
  }
}
