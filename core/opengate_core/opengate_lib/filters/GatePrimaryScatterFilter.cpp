/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePrimaryScatterFilter.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "G4RunManager.hh"
#include "G4Step.hh"

int IsUnscatteredPrimary(const G4Step *step) {
  /*
  Check whether a primary particle initial momentum was changed during this
  step.
  - momentum: direction and energy
  - particles that are not primary are considered as "scatter"
  */
  if (step->GetTrack()->GetParentID() > 0)
    return 0;
  if (step->GetTrack()->GetTrackID() != 1)
    return 0;
  auto *dp = step->GetTrack()->GetDynamicParticle();
  if (dp->GetPrimaryParticle() == nullptr) {
    Fatal("Error in IsUnscatteredPrimary, no DynamicParticle?");
    return -1;
  }
  const auto event_mom = dp->GetPrimaryParticle()->GetMomentum();
  const auto track_mom = step->GetPreStepPoint()->GetMomentum();
  return event_mom.isNear(track_mom);
}

bool GateUnscatteredPrimaryFilter::Accept(G4Step *step) const {
  return (IsUnscatteredPrimary(step) == 1);
}
