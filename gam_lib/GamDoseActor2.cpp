/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamDoseActor2.h"
#include "GamVActor.h"


void GamDoseActor2::BeforeStart() {
    vpositions.resize(batch_size);
}


G4bool GamDoseActor2::ProcessHits(G4Step *step, G4TouchableHistory *touchable) {
    //std::cout << "GamDoseActor2 cpp ProcessHits " << " " << batch_step_count << std::endl;
    /*
     Every step (or hit), the position and edep are stored in a vector.
     Every 'batch_size' step, the SteppingBatchAction function is called (will be overloaded in gam python side)
     */
    SteppingAction(step, touchable);
    ProcessHitsPerBatch();
    return true;
}

void GamDoseActor2::SteppingAction(G4Step *step, G4TouchableHistory *) {
    auto preGlobal = step->GetPreStepPoint()->GetPosition();
    auto touchable = step->GetPreStepPoint()->GetTouchable();
    auto depth = touchable->GetHistoryDepth();
    auto preLocal = touchable->GetHistory()->GetTransform(depth).TransformPoint(preGlobal);
    vpositions[batch_step_count] = preLocal;
}
