/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUserEventInformation.h"
#include "GateHelpers.h"

void GateUserEventInformation::Print() const {
  // FIXME
}

std::string GateUserEventInformation::GetParticleName(G4int track_id) {
  if (fMapOfParticleName.count(track_id) > 0) {
    return fMapOfParticleName.at(track_id);
  } else
    return "unknown";
}

void GateUserEventInformation::BeginOfEventAction(const G4Event *event) {
  fMapOfParticleName.clear();
}

void GateUserEventInformation::PreUserTrackingAction(const G4Track *track) {
  fMapOfParticleName[track->GetTrackID()] =
      track->GetParticleDefinition()->GetParticleName();
}
