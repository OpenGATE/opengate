/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamTrackingAction_h
#define GamTrackingAction_h

#include "G4UserTrackingAction.hh"
#include "G4Track.hh"
#include "GamVActor.h"

class GamTrackingAction : public G4UserTrackingAction {

public:

    GamTrackingAction();

    virtual ~GamTrackingAction() {}

    void RegisterActor(GamVActor *actor);

    virtual void PreUserTrackingAction(const G4Track *Track);

    virtual void PostUserTrackingAction(const G4Track *Track);

protected:
    std::vector<GamVActor *> m_PreUserTrackingAction_actors;
    std::vector<GamVActor *> m_PostUserTrackingAction_actors;
};

#endif // GamTrackingAction_h
