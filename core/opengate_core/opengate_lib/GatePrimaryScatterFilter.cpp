/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePrimaryScatterFilter.h"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

int IsUnscatteredPrimary(const G4Step *step) {
  /*
  Check whether a primary particle initial momentum was changed during this
  step.
  - momentum : direction and energy
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
  auto event_mom = dp->GetPrimaryParticle()->GetMomentum();
  auto track_mom = step->GetPreStepPoint()->GetMomentum();
  return (event_mom.isNear(track_mom));
}

void GateUnscatteredPrimaryFilter::InitializeUserInput(py::dict &user_info) {
  fPolicy = DictGetStr(user_info, "policy");
}

bool GateUnscatteredPrimaryFilter::Accept(G4Step *step) const {
  auto b = IsUnscatteredPrimary(step);
  if (fPolicy == "accept")
    return b == 1;
  if (fPolicy == "reject")
    return b == 0;
  std::ostringstream oss;
  oss << "The policy '" << fPolicy
      << "' for the ScatterFilter is unknown."
         " Use 'accept' or 'reject'";
  Fatal(oss.str());
  return false;
}
