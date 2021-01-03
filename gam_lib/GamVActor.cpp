/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4SDManager.hh"
#include "GamVActor.h"
#include "GamHelpers.h"


GamVActor::GamVActor(std::string name) : G4VPrimitiveScorer(name) {
}

GamVActor::~GamVActor() {
    // The 'Primitives' (Actors here) of the SD should be removed here
    // Otherwise the destructor of the G4RunManager leads to seg fault
    // during destruction (not really clear why)
    for (auto l :fLogicalVolumes) {
        auto currentSD = l->GetSensitiveDetector();
        auto mfd = dynamic_cast<G4MultiFunctionalDetector *>(currentSD);
        for (auto i = 0; i < mfd->GetNumberOfPrimitives(); i++) {
            mfd->RemovePrimitive(mfd->GetPrimitive(i));
        }
    }
}

G4bool GamVActor::ProcessHits(G4Step *step,
                              G4TouchableHistory *touchable) {
    /*
     The second argument is a G4TouchableHistory object for the Readout geometry
     described in the next section. The second argument is NULL if Readout geometry
     is not assigned to this sensitive detector. In this method, one or more G4VHit
     objects should be constructed if the current step is meaningful for your detector.
     */
    SteppingAction(step, touchable);
    return true;
}

void GamVActor::RegisterSD(G4LogicalVolume *lv) {
    // We keep track of all LV to RemovePrimitive in the destructor
    fLogicalVolumes.push_back(lv);
    // Look is a SD already exist for this LV
    auto currentSD = lv->GetSensitiveDetector();
    G4MultiFunctionalDetector *mfd;
    if (!currentSD) {
        // This is the first time a SD is set to this LV
        auto f = new G4MultiFunctionalDetector("mfd_" + lv->GetName());
        G4SDManager::GetSDMpointer()->AddNewDetector(f);
        lv->SetSensitiveDetector(f);
        mfd = f;
    } else {
        // A SD already exist, we reused it
        mfd = dynamic_cast<G4MultiFunctionalDetector *>(currentSD);
    }
    // Register the actor to the G4MultiFunctionalDetector
    mfd->RegisterPrimitive(this);
}

