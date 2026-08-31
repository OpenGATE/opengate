/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateLastInteractionPositionInVolumeAttribute_h
#define GateLastInteractionPositionInVolumeAttribute_h

#include "GateVAuxiliaryAttribute.h"

class GateLastInteractionPositionInVolumeAttribute
    : public GateVAuxiliaryAttribute {
public:
  explicit GateLastInteractionPositionInVolumeAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  G4ThreeVector Get3Value(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;

protected:
  std::string fVolumeName;
  bool fPropagateFromParentTrack{false};
};

#endif // GateLastInteractionPositionInVolumeAttribute_h
