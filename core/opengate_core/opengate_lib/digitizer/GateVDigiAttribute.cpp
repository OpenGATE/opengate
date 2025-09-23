/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVDigiAttribute.h"

GateVDigiAttribute::GateVDigiAttribute(const std::string &vname, char vtype) {
  fDigiAttributeName = vname;
  fDigiAttributeType = vtype;
  fDigiAttributeId = -1;
  fTupleId = -1;
  fProcessHitsFunction = nullptr;
}

GateVDigiAttribute::~GateVDigiAttribute() {}

void GateVDigiAttribute::ProcessHits(G4Step *step) {
  fProcessHitsFunction(this, step);
}

std::vector<double> &GateVDigiAttribute::GetDValues() {
  Fatal("Must never be there ! GateVDigiAttribute D");
  static std::vector<double> fake;
  return fake; // to avoid warning
}

std::vector<int> &GateVDigiAttribute::GetIValues() {
  Fatal("Must never be there ! GateVDigiAttribute I");
  static std::vector<int> fake;
  return fake; // to avoid warning
}

std::vector<int64_t> &GateVDigiAttribute::GetLValues() {
  Fatal("Must never be there ! GateVDigiAttribute L");
  static std::vector<int64_t> fake;
  return fake; // to avoid warning
}

std::vector<std::string> &GateVDigiAttribute::GetSValues() {
  Fatal("Must never be there ! GateVDigiAttribute S");
  static std::vector<std::string> fake;
  return fake; // to avoid warning
}

std::vector<G4ThreeVector> &GateVDigiAttribute::Get3Values() {
  Fatal("Must never be there ! GateVDigiAttribute 3");
  static std::vector<G4ThreeVector> fake;
  return fake; // to avoid warning
}

std::vector<GateUniqueVolumeID::Pointer> &GateVDigiAttribute::GetUValues() {
  Fatal("Must never be there ! GateVDigiAttribute U");
  static std::vector<GateUniqueVolumeID::Pointer> fake;
  return fake; // to avoid warning
}

void GateVDigiAttribute::FillDigiWithEmptyValue() {
  Fatal("Must never be there ! FillDigiWithEmptyValue");
}
