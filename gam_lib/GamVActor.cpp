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

GamVActor::~GamVActor() {}

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

void GamVActor::RegisterSD(G4LogicalVolume *l) {
    fLogicalVolumes.push_back(l);
    // FIXME : check if already set
    // FIXME : allow several volume to be registered.
    auto currentSD = l->GetSensitiveDetector();
    G4MultiFunctionalDetector *mfd;
    if (!currentSD) {
        // std::cout << "first actor for this volume" << std::endl;
        mfd = new G4MultiFunctionalDetector("mfd_" + l->GetName());
        // do not always create check if exist
        // auto pointer
        G4SDManager::GetSDMpointer()->AddNewDetector(mfd);
        l->SetSensitiveDetector(mfd);
    } else {
        // std::cout << "already an actor reuse it" << std::endl;
        mfd = dynamic_cast<G4MultiFunctionalDetector *>(currentSD);
    }
    mfd->RegisterPrimitive(this);
}

