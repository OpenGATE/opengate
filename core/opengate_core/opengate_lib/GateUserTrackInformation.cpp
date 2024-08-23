/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUserTrackInformation.h"
#include "GateHelpers.h"

GateUserTrackInformation::GateUserTrackInformation() { fScatterOrder = 0; }

void GateUserTrackInformation::Print() const {
  // FIXME
}

int GateUserTrackInformation::GetScatterOrder() const { return fScatterOrder; }

void GateUserTrackInformation::Apply(const G4Step *step) {
  DDD(" -> user track apply");
}
