/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamRunAction_h
#define GamRunAction_h

#include "G4UserRunAction.hh"
#include "G4Event.hh"
#include "GamVActor.h"

class GamRunAction : public G4UserRunAction {

public:

    GamRunAction();

    virtual ~GamRunAction() {}

    void RegisterActor(GamVActor *actor);

    virtual void BeginOfRunAction(const G4Run *run);

    virtual void EndOfRunAction(const G4Run *run);

protected:
    std::vector<GamVActor *> fBeginOfRunAction_actors;
    std::vector<GamVActor *> fEndOfRunAction_actors;
};

#endif // GamRunAction_h
