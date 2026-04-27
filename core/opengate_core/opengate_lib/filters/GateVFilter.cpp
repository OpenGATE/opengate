/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVFilter.h"
#include "../GateHelpersDict.h"

GateVFilter::GateVFilter() = default;

GateVFilter::~GateVFilter() = default;

void GateVFilter::InitializeUserInfo(py::dict &user_info) {
  fName = DictGetStr(user_info, "name");
  fNegate =
      user_info.contains("negate") ? DictGetBool(user_info, "negate") : false;
}

bool GateVFilter::Accept(const G4Run *run) const {
  const bool result = Evaluate(run);
  return fNegate ? !result : result;
}

bool GateVFilter::Accept(const G4Event *event) const {
  const bool result = Evaluate(event);
  return fNegate ? !result : result;
}

bool GateVFilter::Accept(const G4Track *track) const {
  const bool result = Evaluate(track);
  return fNegate ? !result : result;
}

bool GateVFilter::Accept(G4Step *step) const {
  const bool result = Evaluate(step);
  return fNegate ? !result : result;
}

bool GateVFilter::Evaluate(const G4Run *) const { return true; }

bool GateVFilter::Evaluate(const G4Event *) const { return true; }

bool GateVFilter::Evaluate(const G4Track *) const { return true; }

bool GateVFilter::Evaluate(G4Step *) const { return true; }
