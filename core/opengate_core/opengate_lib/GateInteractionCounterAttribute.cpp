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

bool GateInteractionCounterAttribute::IsStepCounted(const G4Step *step) const {
  // The process that limited the current step is the one of the post-step
  // point. (The one of the pre-step point limited the previous step.)
  const auto *process = step->GetPostStepPoint()->GetProcessDefinedStep();
  return process != nullptr && process->GetProcessName() == fProcessName;
}

int GateInteractionCounterAttribute::GetIValue(const G4Step *step) const {
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

void GateInteractionCounterAttribute::SteppingAction(const G4Step *step) {
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
