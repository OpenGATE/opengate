/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateLastProcessDefinedStepInVolumeAttribute_h
#define GateLastProcessDefinedStepInVolumeAttribute_h

#include "GateVAuxiliaryAttribute.h"

class GateLastProcessDefinedStepInVolumeAttribute
    : public GateVAuxiliaryAttribute {
public:
  explicit GateLastProcessDefinedStepInVolumeAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  std::string GetSValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;

protected:
  std::string fVolumeName;
  bool fPropagateFromParentTrack{false};
};

#endif // GateLastProcessDefinedStepInVolumeAttribute_h
