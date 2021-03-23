/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVSource.h"
#include "GamHelpers.h"
#include "GamDictHelpers.h"
#include "G4PhysicalVolumeStore.hh"
#include "G4LogicalVolume.hh"

GamVSource::GamVSource() {
    fName = "";
    fStartTime = 0;
    fEndTime = 0;
    fMother = "";
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
    fEventsPerRun.push_back(0);
    fTranslations.clear();
    fRotations.clear();
}

double GamVSource::PrepareNextTime(double current_simulation_time) {
    Fatal("PrepareNextTime must be overloaded");
    return current_simulation_time;
}

void GamVSource::GeneratePrimaries(G4Event */*event*/, double /*time*/) {
    fEventsPerRun.back()++; // FIXME not really used yet
    //Fatal("GeneratePrimaries must be overloaded");
}

void GamVSource::SetOrientationAccordingToMotherVolume(G4Event *event) {
    if (fMother == "world") return;

    if (fTranslations.size() == 0)
        ComputeTransformationAccordingToMotherVolume();

    // Get current position/momentum according to the mother coordinate system
    for (auto vi = 0; vi < event->GetNumberOfPrimaryVertex(); vi++) {
        auto position = event->GetPrimaryVertex(vi)->GetPosition();
        for (size_t i = 0; i < fTranslations.size(); i++) {
            auto t = fTranslations[i];
            auto r = fRotations[i];
            position = r * position;
            position = position + t;
        }
        event->GetPrimaryVertex(vi)->SetPosition(position[0], position[1], position[2]);
        // Loop for all primary in all vertex
        auto n = event->GetPrimaryVertex(vi)->GetNumberOfParticle();
        for (auto pi = 0; pi < n; pi++) {
            auto momentum = event->GetPrimaryVertex(vi)->GetPrimary(pi)->GetMomentumDirection();
            for (size_t i = 0; i < fTranslations.size(); i++) {
                auto r = fRotations[i];
                momentum = r * momentum;
            }
            event->GetPrimaryVertex(vi)->GetPrimary(pi)->SetMomentum(momentum[0], momentum[1], momentum[2]);
        }
    }
}

void GamVSource::ComputeTransformationAccordingToMotherVolume() {
    auto store = G4PhysicalVolumeStore::GetInstance();
    auto vol = store->GetVolume(fMother, false);
    if (vol == nullptr) {
        Fatal("Cannot find the mother volume '" + fMother + "'.");
    }
    while (vol->GetName() != "world") {
        auto r = vol->GetObjectRotationValue();
        auto t = vol->GetObjectTranslation();
        fTranslations.push_back(t);
        fRotations.push_back(r);
        auto name = vol->GetMotherLogical()->GetName();
        vol = store->GetVolume(name, false);
    }
}
