/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateParticleFilter.h"
#include "GateHelpersDict.h"

void GateParticleFilter::InitializeUserInput(py::dict &user_info) {
  fParticleName = DictGetStr(user_info, "particle");
  fPolicy = DictGetStr(user_info, "policy");
}

bool GateParticleFilter::Accept(const G4Track *track) const {
  auto p = track->GetParticleDefinition()->GetParticleName();
  if (p == fParticleName)
    return true;
  return false;
}

bool GateParticleFilter::Accept(G4Step *step) const {
  auto p = step->GetTrack()->GetParticleDefinition()->GetParticleName();
  if (fPolicy == "accept" && p == fParticleName)
    return true;
  if (fPolicy == "reject" && p != fParticleName)
    return true;
  return false;
}
