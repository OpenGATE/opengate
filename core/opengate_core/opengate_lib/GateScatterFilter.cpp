/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateScatterFilter.h"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

int StepHasScatter(const G4Step *step) {
  auto *dp = step->GetTrack()->GetDynamicParticle();
  const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
  // if (step->GetTrack()->GetParentID() != 0) {
  //   return -1;
  // }
  // G4ThreeVector event_mom;
  if (dp->GetPrimaryParticle() == nullptr) {
    DDD(dp->GetParticleDefinition()->GetParticleName());
    DDD(dp->GetDefinition()->GetParticleName());
    DDD(dp->GetKineticEnergy());
    DDD(step->GetTrack()->GetTrackID());
    // event_mom =
    // event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentumDirection();
    // DDD(event_mom);
    // auto track_mom = dp->GetMomentum();
    // DDD(track_mom);
    // DDD(event->GetNumberOfPrimaryVertex());
    // DDD(event->GetPrimaryVertex(0)->GetNumberOfParticle());
    // DDD(step->GetPreStepPoint()->GetProcessDefinedStep()->GetProcessName());
    // DDD(step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName());
    DDD(event->GetEventID());
    return -1;
  }
  auto event_mom = dp->GetPrimaryParticle()->GetMomentum();
  auto track_mom = dp->GetMomentum();
  auto event_mom2 =
      event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentumDirection();
  // DDD(event_mom);
  // DDD(event_mom2);
  // DDD(event_mom.isNear(event_mom2));
  if (event_mom.isNear(track_mom)) {
    // Do not consider scatter if this is a secondary particle
    if (step->GetTrack()->GetTrackID() && step->GetTrack()->GetParentID() > 0)
      return -1;
    else
      return 0;
  } else {
    return 1;
  }
}

void GateScatterFilter::Initialize(py::dict &user_info) {
  // fParticleName = DictGetStr(user_info, "particle");
  fPolicy = DictGetStr(user_info, "policy");
}

bool GateScatterFilter::Accept(G4Step *step) const {
  auto b = StepHasScatter(step);
  /*
   * scatter can be:
   * 1  = particle scattered
   * 0  = particle did not scatter
   * -1 = dont know (not a primary particle or GetPrimaryParticle is null)

   * WARNING !! when -1 (unknown), particle are NOT accepted (filtered)

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
