/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVSource.h"
#include "G4PhysicalVolumeStore.hh"
#include "G4RandomTools.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"

GateVSource::GateVSource() {
  fNumberOfGeneratedEvents = 0;
  fMaxN = 0;
  fActivity = 0;
  fHalfLife = -1;
  fLambda = -1;
  fName = "";
  fStartTime = 0;
  fEndTime = 0;
  fMother = "";
  fLocalTranslation = G4ThreeVector();
  fLocalRotation = G4RotationMatrix();
}

GateVSource::~GateVSource() {}

void GateVSource::InitializeUserInfo(py::dict &user_info) {
  // get info from the dict
  fName = DictGetStr(user_info, "_name");
  fStartTime = DictGetDouble(user_info, "start_time");
  fEndTime = DictGetDouble(user_info, "end_time");
  fMother = DictGetStr(user_info, "mother");

  // get user info about activity or nb of events
  fMaxN = DictGetInt(user_info, "n");
  fActivity = DictGetDouble(user_info, "activity");
  fInitialActivity = fActivity;

  // half life ?
  fHalfLife = DictGetDouble(user_info, "half_life");
  fLambda = log(2) / fHalfLife;
}

void GateVSource::PrepareNextRun() { SetOrientationAccordingToMotherVolume(); }

void GateVSource::UpdateActivity(double time) {
  if (fHalfLife <= 0)
    return;
  fActivity = fInitialActivity * exp(-fLambda * (time - fStartTime));
}

double GateVSource::CalcNextTime(double current_simulation_time) {
  double next_time =
      current_simulation_time - log(G4UniformRand()) * (1.0 / fActivity);
  return next_time;
}

double GateVSource::PrepareNextTime(double current_simulation_time) {
  Fatal("PrepareNextTime must be overloaded");
  return current_simulation_time;
}

void GateVSource::GeneratePrimaries(G4Event * /*event*/, double /*time*/) {
  Fatal("GeneratePrimaries must be overloaded");
}

void GateVSource::SetOrientationAccordingToMotherVolume() {
  fGlobalRotation = fLocalRotation;
  fGlobalTranslation = fLocalTranslation;

  // No change in the translation rotation if mother is the world
  if (fMother == "world")
    return;

  // compute global translation rotation and keep it.
  // Will be used for example in GenericSource to change position
  ComputeTransformationFromVolumeToWorld(fMother, fGlobalTranslation,
                                         fGlobalRotation, false);
}
