/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateLastProcessDefinedStepInVolumeAttribute_h
#define GateLastProcessDefinedStepInVolumeAttribute_h

#include "GateVAuxiliaryAttribute.h"

class G4VProcess;

/*
 * Semantics (same as GateProcessDefinedStepInVolumeAttribute): an interaction
 * is the process of the post-step point (it limited THIS step), when it is
 * not Transportation and the step is in the volume (or its daughters). The
 * value returned for a step includes this step, whether it is read by an
 * actor (before SteppingAction) or after.
 */

class GateLastProcessDefinedStepInVolumeAttribute
    : public GateVAuxiliaryAttribute {
public:
  explicit GateLastProcessDefinedStepInVolumeAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  std::string GetSValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;

protected:
  // the process that limited the current step (post-step point) if it is an
  // interaction (not Transportation) in the volume, nullptr otherwise
  const G4VProcess *GetInteractionInCurrentStep(const G4Step *step) const;

  std::string fVolumeName;
  bool fPropagateFromParentTrack{false};
};

#endif // GateLastProcessDefinedStepInVolumeAttribute_h
