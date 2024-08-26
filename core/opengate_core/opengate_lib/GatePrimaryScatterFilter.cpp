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

int IsPrimaryScatter(const G4Step *step) {
  /*
  Check whether a primary particle initial momentum was changed during this
  step.
  - momentum : direction and energy
  - particles that are not primary are considered as "scatter"
  */
  if (step->GetTrack()->GetParentID() > 0)
    return 1;
  if (step->GetTrack()->GetTrackID() != 1)
    return 1;
  auto *dp = step->GetTrack()->GetDynamicParticle();
  const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
  auto event_id = event->GetEventID();
  if (dp->GetPrimaryParticle() == nullptr) {
    Fatal("Error in IsPrimaryScatter, no DynamicParticle?");
    return -1;
  }
  auto event_mom = dp->GetPrimaryParticle()->GetMomentum();
  auto track_mom = step->GetPreStepPoint()->GetMomentum();
  return (!event_mom.isNear(track_mom));
}

void GatePrimaryScatterFilter::Initialize(py::dict &user_info) {
  fPolicy = DictGetStr(user_info, "policy");
}

bool GatePrimaryScatterFilter::Accept(G4Step *step) const {
  auto b = IsPrimaryScatter(step);
  /*
   * scatter can be:
   * 1  = particle scattered (or is a secondary)
   * 0  = particle did not scatter
   */
  if (fPolicy == "keep_scatter")
    return b == 1;
  if (fPolicy == "keep_no_scatter")
    return b == 0;
  std::ostringstream oss;
  oss << "The policy '" << fPolicy
      << "' for the ScatterFilter is unknown."
         " Use 'keep_scatter' or 'keep_no_scatter'";
  Fatal(oss.str());
  return false;
}
