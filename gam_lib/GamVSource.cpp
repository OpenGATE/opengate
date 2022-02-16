/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVSource.h"
#include "GamHelpers.h"
#include "GamHelpersDict.h"
#include "G4PhysicalVolumeStore.hh"
#include "G4LogicalVolume.hh"

GamVSource::GamVSource() {
    fName = "";
    fStartTime = 0;
    fEndTime = 0;
    fMother = "";
    fLocalTranslation = G4ThreeVector();
    fLocalRotation = G4RotationMatrix();
}

GamVSource::~GamVSource() {}

void GamVSource::InitializeUserInfo(py::dict &user_info) {
    // get info from the dict
    fName = DictStr(user_info, "name");
    fStartTime = DictFloat(user_info, "start_time");
    fEndTime = DictFloat(user_info, "end_time");
    fMother = DictStr(user_info, "mother");
}

void GamVSource::PrepareNextRun() {
    SetOrientationAccordingToMotherVolume();
}

double GamVSource::PrepareNextTime(double current_simulation_time) {
    Fatal("PrepareNextTime must be overloaded");
    return current_simulation_time;
}

void GamVSource::GeneratePrimaries(G4Event */*event*/, double /*time*/) {
    //fEventsPerRun.back()++; // FIXME not really used yet
    Fatal("GeneratePrimaries must be overloaded");
}

void GamVSource::SetOrientationAccordingToMotherVolume() {
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
        fGlobalTranslation = fGlobalRotation * fGlobalTranslation + fTranslations[i];
    }
}


void GamVSource::ComputeTransformationAccordingToMotherVolume() {
    auto store = G4PhysicalVolumeStore::GetInstance();
    auto vol = store->GetVolume(fMother, false);
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
