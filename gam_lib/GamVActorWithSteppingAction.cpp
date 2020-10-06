/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVActorWithSteppingAction.h"
#include "GamVActor.h"
#include "G4TouchableHistory.hh"

void GamVActorWithSteppingAction::BeforeStart() {

}


G4bool GamVActorWithSteppingAction::ProcessHits(G4Step *step, G4TouchableHistory *touchable) {
    SteppingAction(step, touchable);
    //ProcessHitsPerBatch(); // not needed FIXME test only
    // std::cout << "End ProcessHits" << std::endl;
    return true;
}

void GamVActorWithSteppingAction::SteppingAction(G4Step *, G4TouchableHistory *) {
    // will be overloaded on py side
}
