/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4SDManager.hh"
#include "GamVActor.h"
#include "GamHelpersDict.h"
#include "GamHelpers.h"
#include "GamMultiFunctionalDetector.h"
#include "GamActorManager.h"

GamVActor::GamVActor(py::dict &user_info) :
    G4VPrimitiveScorer(DictGetStr(user_info, "name")) {
    fMotherVolumeName = DictGetStr(user_info, "mother");
    // register this actor to the global list of actors
    GamActorManager::AddActor(this);
}

GamVActor::~GamVActor() {
}

void GamVActor::AddActions(std::set<std::string> &actions) {
    fActions.insert(actions.begin(), actions.end());
}

void GamVActor::PreUserTrackingAction(const G4Track *track) {
    for (auto f: fFilters) {
        if (!f->Accept(track)) return;
    }
}

void GamVActor::PostUserTrackingAction(const G4Track *track) {
    for (auto f: fFilters) {
        if (!f->Accept(track)) return;
    }
}

G4bool GamVActor::ProcessHits(G4Step *step, G4TouchableHistory *) {
    /*
     In the G4 docs:

     "The second argument is a G4TouchableHistory object for the Readout geometry
     described in the next section. The second argument is NULL if Readout geometry
     is not assigned to this sensitive detector. In this method, one or more G4VHit
     objects should be constructed if the current step is meaningful for your detector."

     "The second argument of FillHits() method, i.e. G4TouchableHistory, is obsolete and not used.
     If user needs to define an artificial second geometry, use Parallel Geometries."

      => so we decide to simplify and remove "touchable" in the following.
     */

    for (auto f: fFilters) {
        if (!f->Accept(step)) return true;
    }
    SteppingAction(step);
    return true;
}

void GamVActor::RegisterSD(G4LogicalVolume *lv) {
    // Look is a SD already exist for this LV
    auto currentSD = lv->GetSensitiveDetector();
    GamMultiFunctionalDetector *mfd;
    if (!currentSD) {
        // This is the first time a SD is set to this LV
        auto f = new GamMultiFunctionalDetector("mfd_" + lv->GetName());
        G4SDManager::GetSDMpointer()->AddNewDetector(f);
        lv->SetSensitiveDetector(f);
        mfd = f;
    } else {
        // A SD already exist, we reused it
        mfd = dynamic_cast<GamMultiFunctionalDetector *>(currentSD);
        for (auto i = 0; i < mfd->GetNumberOfPrimitives(); i++) {
            if (mfd->GetPrimitive(i)->GetName() == GetName()) {
                // In that case the actor is already registered, we skip to avoid
                // G4 exception. It happens when the LogVol has several PhysVol (repeater)
                return;
            }
        }
    }
    // Register the actor to the GamMultiFunctionalDetector
    mfd->RegisterPrimitive(this);
}

