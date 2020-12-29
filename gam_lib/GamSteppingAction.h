/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSteppingAction_h
#define GamSteppingAction_h

#include "G4UserSteppingAction.hh"
#include "G4Step.hh"
#include "GamVActor.h"

class GamSteppingAction : public G4UserSteppingAction {

public:

    GamSteppingAction();

    virtual ~GamSteppingAction() {}

    void RegisterActor(GamVActor *actor);

    virtual void UserSteppingAction(const G4Step *step);

protected:
    std::vector<GamVActor *> fUserSteppingActionActors;
};

#endif // GamSteppingAction_h
