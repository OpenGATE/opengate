/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "GateTLEDoseActor.h"

#include <cmath>
#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>
#include <queue>
#include <vector>

GateTLEDoseActor::GateTLEDoseActor(py::dict &user_info)
    : GateDoseActor(user_info) {
  // FIXME WARNING : not checked for MT
}

void GateTLEDoseActor::InitializeUserInput(py::dict &user_info) {
  GateDoseActor::InitializeUserInput(user_info);
}

void GateTLEDoseActor::InitializeCpp() { GateDoseActor::InitializeCpp(); }

void GateTLEDoseActor::BeginOfRunActionMasterThread(int run_id) {
  GateDoseActor::BeginOfRunActionMasterThread(run_id);
}

void GateTLEDoseActor::BeginOfRunAction(const G4Run *run) {
  GateDoseActor::BeginOfRunAction(run);
}

void GateTLEDoseActor::BeginOfEventAction(const G4Event *event) {
  GateDoseActor::BeginOfEventAction(event);
}

void GateTLEDoseActor::SteppingAction(G4Step *step) {
  GateDoseActor::SteppingAction(step);
}

void GateTLEDoseActor::EndOfRunAction(const G4Run *run) {
  GateDoseActor::EndOfRunAction(run);
}

int GateTLEDoseActor::EndOfRunActionMasterThread(int run_id) {
  return GateDoseActor::EndOfRunActionMasterThread(run_id);
}
