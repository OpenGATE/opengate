/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateInteractionCounterAttribute_h
#define GateInteractionCounterAttribute_h

#include "GateProcessDefinedStepInVolumeAttribute.h"
#include "GateVAuxiliaryAttribute.h"

/*
 * Count how often a given process defined a step of the current track.
 * Same semantics as GateProcessDefinedStepInVolumeAttribute (without the
 * volumes): the process is the one of the post-step point (it limited THIS
 * step), and the value returned for a step includes this step, whether it is
 * read by an actor (before SteppingAction) or after.
 */

class GateInteractionCounterAttribute : public GateVAuxiliaryAttribute {
public:
  explicit GateInteractionCounterAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  int GetIValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;

protected:
  bool IsStepCounted(const G4Step *step) const;

  std::string fProcessName;
  bool fPropagateFromParentTrack{false};
};

#endif // GateInteractionCounterAttribute_h
