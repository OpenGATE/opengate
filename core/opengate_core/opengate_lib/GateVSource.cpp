/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVSource.h"
#include "G4PhysicalVolumeStore.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"

G4Mutex SourceOrientationMutex = G4MUTEX_INITIALIZER;

GateVSource::GateVSource() {
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
}

void GateVSource::PrepareNextRun() { SetOrientationAccordingToMotherVolume(); }

double GateVSource::PrepareNextTime(double current_simulation_time) {
  Fatal("PrepareNextTime must be overloaded");
  return current_simulation_time;
}

void GateVSource::GeneratePrimaries(G4Event * /*event*/, double /*time*/) {
  Fatal("GeneratePrimaries must be overloaded");
}

void GateVSource::SetOrientationAccordingToMotherVolume() {
  auto &l = fThreadLocalData.Get();
  l.fGlobalRotation = fLocalRotation;
  l.fGlobalTranslation = fLocalTranslation;

  // No change in the translation rotation if mother is the world
  if (fMother == "world")
    return;

  // compute global translation rotation and keep it.
  // Will be used for example in GenericSource to change position
  ComputeTransformationFromVolumeToWorld(fMother, l.fGlobalTranslation,
                                         l.fGlobalRotation, false);
}
