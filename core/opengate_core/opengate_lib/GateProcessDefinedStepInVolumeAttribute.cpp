/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateProcessDefinedStepInVolumeAttribute.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"
#include <G4LogicalVolume.hh>
#include <G4LogicalVolumeStore.hh>
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
  // volume_name is either a single name or a list of names
  fVolumeNames.clear();
  if (py::isinstance<py::str>(user_info["volume_name"]))
    fVolumeNames.push_back(DictGetStr(user_info, "volume_name"));
  else if (!user_info["volume_name"].is_none())
    fVolumeNames = DictGetVecStr(user_info, "volume_name");
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

bool GateProcessDefinedStepInVolumeAttribute::IsStepInVolumes(
    const G4Step *step) const {
  auto &l = fThreadLocalData.Get();
  if (!l.fResolved) {
    // Several logical volumes may share a name: keep them all.
    for (const auto *lv : *G4LogicalVolumeStore::GetInstance()) {
      for (const auto &name : fVolumeNames) {
        if (lv->GetName() == name) {
          l.fLogicalVolumes.push_back(lv);
          break;
        }
      }
    }
    l.fResolved = true;
  }
  const auto &touchable = step->GetPreStepPoint()->GetTouchableHandle();
  if (touchable->GetVolume() == nullptr)
    return false;
  // The step is in a volume if this volume is found anywhere in the touchable
  // history: steps in the daughters are counted.
  const auto history_depth = touchable->GetHistoryDepth();
  for (int depth = 0; depth <= history_depth; depth++) {
    const auto *physical_volume = touchable->GetVolume(depth);
    if (physical_volume == nullptr)
      continue;
    const auto *lv = physical_volume->GetLogicalVolume();
    for (const auto *v : l.fLogicalVolumes) {
      if (v == lv)
        return true;
    }
  }
  return false;
}

bool GateProcessDefinedStepInVolumeAttribute::IsStepCounted(
    const G4Step *step) const {
  // The process that limited the current step is the one of the post-step
  // point. (The one of the pre-step point limited the previous step.)
  const auto *process = step->GetPostStepPoint()->GetProcessDefinedStep();
  if (process == nullptr || process->GetProcessName() != fProcessName)
    return false;
  return IsStepInVolumes(step);
}

int GateProcessDefinedStepInVolumeAttribute::GetIValue(
    const G4Step *step) const {
  if (step == nullptr)
    return 0;
  const auto *track = step->GetTrack();
  const auto *info =
      GetTrackData<GateProcessDefinedStepCounterTrackData>(track);
  int count = 0;
  int last_counted_step = 0;
  if (info != nullptr) {
    count = info->GetCount();
    last_counted_step = info->fLastCountedStepNumber;
  }
  // The actors (sensitive detectors) read the value before SteppingAction is
  // called for the current step: account for it here, so that the value does
  // not depend on the moment it is read.
  if (last_counted_step != track->GetCurrentStepNumber() && IsStepCounted(step))
    count++;
  return count;
}

void GateProcessDefinedStepInVolumeAttribute::SteppingAction(
    const G4Step *step) {
  const auto *track = step->GetTrack();
  if (IsStepCounted(step)) {
    auto *info =
        GetOrCreateTrackData<GateProcessDefinedStepCounterTrackData>(track);
    info->Increment();
    info->fLastCountedStepNumber = track->GetCurrentStepNumber();
  }

  if (fPropagateFromParentTrack) {
    // Only the count is given to the secondaries (not the step bookkeeping,
    // which is relative to the parent track).
    const auto *info =
        GetTrackData<GateProcessDefinedStepCounterTrackData>(track);
    if (info != nullptr && info->GetCount() > 0) {
      SetStoredTrackDataValueOnSecondariesInCurrentStep<
          GateProcessDefinedStepCounterTrackData, int>(step, info->GetCount());
    }
  }
}
