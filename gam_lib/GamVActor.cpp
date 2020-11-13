/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVActor.h"
#include "G4SDManager.hh"


GamVActor::GamVActor(std::string name) : G4VPrimitiveScorer(name) {
    batch_size = 10000;
}

GamVActor::~GamVActor() {
}


void GamVActor::StartSimulationAction() {
    batch_step_count = 0;
}


G4bool GamVActor::ProcessHits(G4Step * /*step*/,
                              G4TouchableHistory * /*touchable*/) {
    /*
     The second argument is a G4TouchableHistory object for the Readout geometry
     described in the next section. The second argument is NULL if Readout geometry
     is not assigned to this sensitive detector. In this method, one or more G4VHit
     objects should be constructed if the current step is meaningful for your detector.
     */
    //ProcessHitsPerBatch();
    SteppingBatchAction();
    return true;
}

void GamVActor::RegisterSD(G4LogicalVolume *l) {
    logicalVolumes.push_back(l);
    // std::cout << "GamVActor RegisterSD " << std::endl;
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


void GamVActor::ProcessHitsPerBatch(bool force) {
    // All hits go here.
    // Trigger SteppingBatchAction if batch is full
    // Can be overridden by the actors
    if (batch_step_count >= batch_size || force) {
        SteppingBatchAction();
        batch_step_count = 0;
        return;
    }
    batch_step_count++;
}

void GamVActor::EndOfRunAction(const G4Run * /*run*/) {
    //std::cout << "EndOfRunAction , processHistperBatch "
    //<< batch_step_count << " " << batch_size << std::endl;
    // Needed to process the remaining information in current non-terminated batch
    ProcessHitsPerBatch(true);
}