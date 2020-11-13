/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamEventAction_h
#define GamEventAction_h

#include "G4UserEventAction.hh"
#include "G4Event.hh"
#include "GamVActor.h"

class GamEventAction : public G4UserEventAction {

public:

    GamEventAction();

    virtual ~GamEventAction() {}

    void RegisterActor(GamVActor *actor);

    virtual void BeginOfEventAction(const G4Event *event);

    virtual void EndOfEventAction(const G4Event *event);

protected:
    std::vector<GamVActor *> m_BeginOfEventAction_actors;
    std::vector<GamVActor *> m_EndOfEventAction_actors;
};

#endif // GamEventAction_h
