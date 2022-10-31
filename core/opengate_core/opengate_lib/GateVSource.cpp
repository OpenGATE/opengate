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
  fName = DictGetStr(user_info, "name");
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
  // No change in the translation rotation if mother is the world
  if (fMother == "world") {
    fGlobalTranslation = fLocalTranslation;
    fGlobalRotation = fLocalRotation;
    return;
  }

  // compute global translation rotation and keep it.
  // Will be used for example in GenericSource to change position
  ComputeTransformationAccordingToMotherVolume();
  fGlobalRotation = fLocalRotation;
  fGlobalTranslation = fLocalTranslation;
  for (unsigned int i = 0; i < fRotations.size(); i++) {
    fGlobalRotation = fRotations[i] * fGlobalRotation;
    fGlobalTranslation =
        fGlobalRotation * fGlobalTranslation + fTranslations[i];
  }
}

void GateVSource::ComputeTransformationAccordingToMotherVolume() {
  auto *store = G4PhysicalVolumeStore::GetInstance();
  auto *vol = store->GetVolume(fMother, false);
  if (vol == nullptr) {
    Fatal("Cannot find the mother volume '" + fMother + "'.");
  }
  fTranslations.clear();
  fRotations.clear();
  while (vol->GetName() != "world") {
    auto r = vol->GetObjectRotationValue();
    auto t = vol->GetObjectTranslation();
    fTranslations.push_back(t);
    fRotations.push_back(r);
    auto name = vol->GetMotherLogical()->GetName();
    vol = store->GetVolume(name, false);
  }
}
