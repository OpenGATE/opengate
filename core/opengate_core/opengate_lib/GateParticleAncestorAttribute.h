/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateParticleAncestorAttribute_h
#define GateParticleAncestorAttribute_h

#include "GateVAuxiliaryAttribute.h"

class GateParticleAncestorAttribute : public GateVAuxiliaryAttribute {
public:
  explicit GateParticleAncestorAttribute(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;
  void InitializeCpp() override;
  G4ThreeVector Get3Value(const G4Step *step) const override;
  double GetDValue(const G4Step *step) const override;
  void SteppingAction(const G4Step *step) override;
  void PreUserTrackingAction(const G4Track *track) override;

  std::string fAttributeToStore;
  std::string fParticleName;
};

#endif // GateParticleAncestorAttribute_h
