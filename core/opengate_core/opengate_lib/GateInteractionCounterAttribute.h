/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateInteractionCounterAttribute_h
#define GateInteractionCounterAttribute_h

#include "GateVAuxiliaryAttribute.h"

class GateInteractionCounterAttribute : public GateVAuxiliaryAttribute {
public:
  explicit GateInteractionCounterAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  int GetIValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;

protected:
  std::string fProcessName;
  bool fPropagateFromParentTrack{false};
};

#endif // GateInteractionCounterAttribute_h
