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

GamVSource::~GamVSource() {
    DDD("destructor GamVsource source");

    //G4MUTEXDESTROY(mutex);
}

std::string GamVSource::Dump(std::string s) {
    std::ostringstream oss;
    oss << s
        << "fEventsPerRun = " << fEventsPerRun.size() << std::endl
        << "fName = " << fName << std::endl
        << " fStartTime = " << fStartTime << std::endl
        << "fEndTime = " << fEndTime << std::endl
        << "fMother = " << fMother << std::endl
        << "fTranslations = " << fTranslations.size() << std::endl
        << "fRotations = " << fRotations.size() << std::endl;
    return oss.str();
}


GamVSource *GamVSource::Clone(GamVSource *currentClone) {
    DDD("Clone VSource");
    if (currentClone == nullptr)
        currentClone = new GamVSource();
    currentClone->fEventsPerRun = fEventsPerRun;
    currentClone->fName = fName;
    currentClone->fStartTime = fStartTime;
    currentClone->fEndTime = fEndTime;
    currentClone->fMother = fMother;
    currentClone->fTranslations = fTranslations;
    currentClone->fRotations = fRotations;
    return currentClone;
}


void GamVSource::InitializeUserInfo(py::dict &user_info) {
    //DDD("before GamVSource source mutex");
    DDD("InitializeUserInfo");
    //
    //G4MUTEXINIT(mutex);
    //G4AutoLock l(&mutex);

    // FIXME replace by DicStr etc (check)
    fName = DictStr(user_info, "name");
    fStartTime = DictFloat(user_info, "start_time");
    fEndTime = DictFloat(user_info, "end_time");
    fMother = DictStr(user_info, "mother");
    DDD("GamVSource::InitializeUserInfo");
    DDD(fEndTime);
}

void GamVSource::PrepareNextRun() {
    DDD("PrepareNextRun");
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
