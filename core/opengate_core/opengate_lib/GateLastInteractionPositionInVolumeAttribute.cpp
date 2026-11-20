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
#include <limits>

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

const G4VProcess *
GateLastInteractionPositionInVolumeAttribute::GetInteractionInCurrentStep(
    const G4Step *step) const {
  const auto *process = step->GetPostStepPoint()->GetProcessDefinedStep();
  if (process == nullptr || process->GetProcessName() == "Transportation")
    return nullptr;
  if (!IsStepInVolume(step, fVolumeName))
    return nullptr;
  return process;
}

G4ThreeVector GateLastInteractionPositionInVolumeAttribute::Get3Value(
    const G4Step *step) const {
  // Use NaN as the public "unset" sentinel so analysis code can distinguish
  // "no qualifying interaction seen yet" from a real interaction at (0, 0, 0).
  const auto nan = std::numeric_limits<double>::quiet_NaN();
  if (step == nullptr)
    return {nan, nan, nan};
  // the current step first (actors read it before SteppingAction): the
  // interaction is at the post-step point
  if (GetInteractionInCurrentStep(step) != nullptr)
    return step->GetPostStepPoint()->GetPosition();
  return GetStoredTrackDataValue<GateThreeVectorTrackData, G4ThreeVector>(
      step, G4ThreeVector(nan, nan, nan));
}

void GateLastInteractionPositionInVolumeAttribute::SteppingAction(
    const G4Step *step) {
  if (GetInteractionInCurrentStep(step) != nullptr) {
    SetStoredTrackDataValue<GateThreeVectorTrackData, G4ThreeVector>(
        step->GetTrack(), step->GetPostStepPoint()->GetPosition());
  }

  if (fPropagateFromParentTrack) {
    PropagateTrackDataToSecondariesInCurrentStep<GateThreeVectorTrackData>(
        step);
  }
}
