/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVHitAttribute.h"

GateVHitAttribute::GateVHitAttribute(std::string vname, char vtype) {
  fHitAttributeName = vname;
  fHitAttributeType = vtype;
}

GateVHitAttribute::~GateVHitAttribute() {}

void GateVHitAttribute::ProcessHits(G4Step *step) {
  fProcessHitsFunction(this, step);
}

std::vector<double> &GateVHitAttribute::GetDValues() {
  Fatal("Must never be there ! GateVHitAttribute D");
  static std::vector<double> fake;
  return fake; // to avoid warning
}

std::vector<int> &GateVHitAttribute::GetIValues() {
  Fatal("Must never be there ! GateVHitAttribute I");
  static std::vector<int> fake;
  return fake; // to avoid warning
}

std::vector<std::string> &GateVHitAttribute::GetSValues() {
  Fatal("Must never be there ! GateVHitAttribute S");
  static std::vector<std::string> fake;
  return fake; // to avoid warning
}

std::vector<G4ThreeVector> &GateVHitAttribute::Get3Values() {
  Fatal("Must never be there ! GateVHitAttribute 3");
  static std::vector<G4ThreeVector> fake;
  return fake; // to avoid warning
}

std::vector<GateUniqueVolumeID::Pointer> &GateVHitAttribute::GetUValues() {
  Fatal("Must never be there ! GateVHitAttribute U");
  static std::vector<GateUniqueVolumeID::Pointer> fake;
  return fake; // to avoid warning
}

void GateVHitAttribute::FillHitWithEmptyValue() {
  Fatal("Must never be there ! FillHitWithEmptyValue");
}
