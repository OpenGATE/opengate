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


GamARFActor::GamARFActor(py::dict &user_info) : GamVActor(user_info, false) {
    fActions.insert("SteppingAction");
    // Option: batch size
    fBatchSize = DictGetInt(user_info, "batch_size");
    fCurrentNumberOfHits = 0;
}

void GamARFActor::SetARFFunction(ARFFunctionType &f) {
    fApply = f;
}

void GamARFActor::SteppingAction(G4Step *step) {
    fCurrentNumberOfHits++;

    // get energy
    auto *pre = step->GetPreStepPoint();
    fEnergy.push_back(pre->GetKineticEnergy());

    // get position and transform to local
    auto pos = pre->GetTouchable()->GetHistory()->GetTopTransform().TransformPoint(pre->GetPosition());
    fPositionX.push_back(pos[0]);
    fPositionY.push_back(pos[1]);

    // get direction and transform to local
    auto dir = pre->GetMomentumDirection();
    dir = pre->GetTouchable()->GetHistory()->GetTopTransform().TransformAxis(dir);
    fDirectionX.push_back(dir[0]);
    fDirectionY.push_back(dir[1]);

    // trigger the "apply" if the number of batch is reached
    if (fCurrentNumberOfHits >= fBatchSize) {
        fApply(this);
        fEnergy.clear();
        fPositionX.clear();
        fPositionY.clear();
        fDirectionX.clear();
        fDirectionY.clear();
        fCurrentNumberOfHits = 0;
    }
}