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

G4Mutex SetNbKillMutex = G4MUTEX_INITIALIZER;

GateKillActor::GateKillActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("SteppingAction");
  fNbOfKilledParticles = 0;
}

void GateKillActor::ActorInitialize() {}

void GateKillActor::StartSimulationAction() { fNbOfKilledParticles = 0; }

void GateKillActor::SteppingAction(G4Step *step) {
  auto track = step->GetTrack();
  track->SetTrackStatus(fStopAndKill);
  G4AutoLock mutex(&SetNbKillMutex);
  fNbOfKilledParticles++;
}
