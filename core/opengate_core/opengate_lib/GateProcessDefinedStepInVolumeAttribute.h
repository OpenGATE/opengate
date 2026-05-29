/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateProcessDefinedStepInVolumeAttribute_h
#define GateProcessDefinedStepInVolumeAttribute_h

#include "GateTrackData.h"
#include "GateVAuxiliaryAttribute.h"

class GateProcessDefinedStepInVolumeAttribute : public GateVAuxiliaryAttribute {
public:
  explicit GateProcessDefinedStepInVolumeAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  int GetIValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;

protected:
  std::string fProcessName;
  std::string fVolumeName;
  bool fPropagateFromParentTrack{false};
};

#endif // GateProcessDefinedStepInVolumeAttribute_h
