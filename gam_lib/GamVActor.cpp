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
    //fMFDetector = nullptr;
}

GamVActor::~GamVActor() {
    std::cout << "G4 GAM dest GamVActor" << std::endl;
    std::cout << " fmf " << fMFDetectors.size() << std::endl;
    std::cout << "LV " << fLogicalVolumes.size() << std::endl;

    // try to delete the primitive
    /*
    for (auto const&[key, val] : fMFDetectors) {
        std::cout << "remove " << key << " " << fPrimitives[key].size() << std::endl;
        for (auto p:fPrimitives[key]) {
            std::cout << " --> remove " << p->GetName() << std::endl;
            val->RemovePrimitive(p);
        }
    }
     */

    for (auto l :fLogicalVolumes) {
        std::cout << "For LV " << l->GetName() << std::endl;
        auto currentSD = l->GetSensitiveDetector();
        auto mfd = dynamic_cast<G4MultiFunctionalDetector *>(currentSD);
        std::cout << "number of primitives " << mfd->GetNumberOfPrimitives() << std::endl;
        for (auto i = 0; i < mfd->GetNumberOfPrimitives(); i++) {
            std::cout << "Remove primitive " << l->GetName() << " ===> " << i << std::endl;
            mfd->RemovePrimitive(mfd->GetPrimitive(i));
        }
        //std::cout << "Remove primitive" << GetName() << std::endl;
        //mfd->RemovePrimitive(this);
    }

    // delete fMFDetector;
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

void GamVActor::RegisterSD(G4LogicalVolume *l) {
    fLogicalVolumes.push_back(l);
    // FIXME : check if already set
    // FIXME : allow several volume to be registered.
    auto currentSD = l->GetSensitiveDetector(); //FIXME
    G4MultiFunctionalDetector *mfd;
    //if (!currentSD) {
    //if (fMFDetector == nullptr) {
    DDD(l->GetName());
    //if (fMFDetectors.find(l->GetName()) == fMFDetectors.end()) {
    if (!currentSD) {
        std::cout << "first actor for this volume " << std::endl;
        auto f = new G4MultiFunctionalDetector("mfd_" + l->GetName());
        // do not always create check if exist
        // auto pointer
        G4SDManager::GetSDMpointer()->AddNewDetector(f);
        l->SetSensitiveDetector(f);
        //fMFDetectors[l->GetName()] = f;
        mfd = f;
    } else {
        std::cout << "already an actor reuse it" << std::endl;
        //fMFDetector = dynamic_cast<G4MultiFunctionalDetector *>(currentSD);
        mfd = dynamic_cast<G4MultiFunctionalDetector *>(currentSD);
    }
    //FIXME
    //fMFDetectors[l->GetName()]->RegisterPrimitive(this);
    mfd->RegisterPrimitive(this);
    //fPrimitives[l->GetName()].push_back(this);
    std::cout << "RegisterSD add primitive " << l->GetName() << " " << GetName() << std::endl;
    std::cout << "RegisterSD add primitive " << fPrimitives[l->GetName()].size() << std::endl;
}

