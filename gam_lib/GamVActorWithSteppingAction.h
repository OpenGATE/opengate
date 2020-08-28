/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVActorWithSteppingAction_h
#define GamVActorWithSteppingAction_h

#include "G4VPrimitiveScorer.hh"
#include "GamVActor.h"

class GamVActorWithSteppingAction : public GamVActor {

public:

    GamVActorWithSteppingAction(std::string name) : GamVActor(name) {}

    virtual void BeforeStart();

    virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

};

#endif // GamVActorWithSteppingAction_h
