/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateEventAction_h
#define GateEventAction_h

#include "G4UserEventAction.hh"
#include "G4Event.hh"
#include "GateVActor.h"

class GateEventAction : public G4UserEventAction {

public:

    GateEventAction();

    virtual ~GateEventAction() {}

    void RegisterActor(GateVActor *actor);

    virtual void BeginOfEventAction(const G4Event *event);

    virtual void EndOfEventAction(const G4Event *event);

protected:
    std::vector<GateVActor *> fBeginOfEventAction_actors;
    std::vector<GateVActor *> fEndOfEventAction_actors;
};

#endif // GateEventAction_h
