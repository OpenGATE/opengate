/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4RandomTools.hh"
#include "G4Navigator.hh"
#include "G4RunManager.hh"
#include "GamARFActor.h"
#include "GamHelpersImage.h"
#include "GamHelpers.h"
#include "GamHelpersDict.h"


GamARFActor::GamARFActor(py::dict &user_info) : GamVActor(user_info) {
    fActions.insert("BeginOfRunAction");
    fActions.insert("SteppingAction");
    fActions.insert("EndSimulationAction");
    // Option: batch size
    fBatchSize = DictGetInt(user_info, "batch_size");
    DDD(fBatchSize);
}

void GamARFActor::ActorInitialize() {
    DDD("ActorInitialize");
}

void GamARFActor::SetARFFunction(ARFFunctionType &f) {
    fApply = f;
}


void GamARFActor::BeginOfRunAction(const G4Run *) {
    DDD("BeginOfRunAction");
    fCurrentNumberOfHits = 0;

    // FIXME check if apply is ok
}

void GamARFActor::SteppingAction(G4Step *step) {
    fCurrentNumberOfHits++;
    auto *pre = step->GetPreStepPoint();

    fEnergy.push_back(pre->GetKineticEnergy());
    auto pos = pre->GetTouchable()->GetHistory()->GetTopTransform().TransformPoint(pre->GetPosition());
    fPositionX.push_back(pos[0]);
    fPositionY.push_back(pos[1]);
    auto dir = pre->GetMomentumDirection();
    dir = pre->GetTouchable()->GetHistory()->GetTopTransform().TransformAxis(dir);
    fDirectionX.push_back(dir[0]);
    fDirectionY.push_back(dir[1]);

    if (fCurrentNumberOfHits >= fBatchSize) {
        fApply(this);
        // FIXME mNumberOfBatch++;
        fCurrentNumberOfHits = 0;
        fEnergy.clear();
        fPositionX.clear();
        fPositionY.clear();
        fDirectionX.clear();
        fDirectionY.clear();
    }
}

// FIXME warning: end of event -> if event do not reach the detector ?

void GamARFActor::EndSimulationAction() {
    DDD("EndSimulationAction");
    DDD(fCurrentNumberOfHits);
}
