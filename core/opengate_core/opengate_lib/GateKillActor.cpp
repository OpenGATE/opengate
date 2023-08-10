/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateKillActor.h"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

GateKillActor::GateKillActor(py::dict &user_info)
    : GateVActor(user_info, true) {

  // Action for this actor: during stepping

  fActions.insert("SteppingAction");
  fActions.insert("EndSimulationAction");
  fKillFlag = DictGetBool(user_info, "kill");
}

void GateKillActor::ActorInitialize() {}

void GateKillActor::SteppingAction(G4Step *step) {
  if (fKillFlag) {
    auto track = step->GetTrack();
    track->SetTrackStatus(fStopAndKill);
  }
}

void GateKillActor::EndSimulationAction() {}
