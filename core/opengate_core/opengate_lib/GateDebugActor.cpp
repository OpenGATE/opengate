/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4Electron.hh"
#include "G4Gamma.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateDebugActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include <cmath>
#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>
#include <queue>
#include <vector>

GateDebugActor::GateDebugActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  DDD("(cpp) DebugActor constructor")
}

void GateDebugActor::InitializeUserInfo(py::dict &user_info) {
  DDD("(cpp) DebugActor::InitializeUserInfo")
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);
}

void GateDebugActor::InitializeCpp() {
  DDD("(cpp) DebugActor::InitializeCpp")
  GateVActor::InitializeCpp();
}

void GateDebugActor::BeginOfRunActionMasterThread(int run_id) {
  DDD("(cpp) GateDebugActor::BeginOfRunActionMasterThread")
}

void GateDebugActor::BeginOfRunAction(const G4Run *run) {
  DDD("(cpp) GateDebugActor::BeginOfRunAction", " ", run->GetRunID());
}

void GateDebugActor::BeginOfEventAction(const G4Event *event) {
  DDD("(cpp) GateDebugActor::BeginOfEventAction", event->GetEventID());
}

void GateDebugActor::PreUserTrackingAction(const G4Track *track) {
  DDD("(cpp) GateDebugActor::PreUserTrackingAction", " ", track->GetTrackID());
}

void GateDebugActor::PostUserTrackingAction(const G4Track *track) {
  DDD("(cpp) GateDebugActor::PostUserTrackingAction", " ", track->GetTrackID());
}

void GateDebugActor::SteppingAction(G4Step *step) {
  DDD("(cpp) GateDebugActor::SteppingAction", " ",
      step->GetTrack()->GetCurrentStepNumber());
}

void GateDebugActor::EndOfEventAction(const G4Event *event) {
  DDD("(cpp) GateDebugActor::EndOfEventAction", " ", event->GetEventID());
}

int GateDebugActor::EndOfRunActionMasterThread(int run_id) {
  DDD("(cpp) GateDebugActor::EndOfRunActionMasterThread")
  return 0;
}

void GateDebugActor::EndOfRunAction(const G4Run *run) {
  DDD("(cpp) GateDebugActor::EndOfRunAction", " ", run->GetRunID());
}
