/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateGammaAncestorAttribute_h
#define GateGammaAncestorAttribute_h

#include "GateVAuxiliaryAttribute.h"

class GateGammaAncestorAttribute : public GateVAuxiliaryAttribute {
public:
  explicit GateGammaAncestorAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  G4ThreeVector Get3Value(const G4Step *step) const override;
  double GetDValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;
  void PreUserTrackingAction(const G4Track *track) override;

  std::string fAttributeToStore;
};

#endif // GateGammaAncestorAttribute_h
