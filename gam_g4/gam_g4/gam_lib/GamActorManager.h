/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamActorManager_h
#define GamActorManager_h

#include "GamVActor.h"

class GamActorManager {
public:

    static GamActorManager *GetInstance();

    virtual ~GamActorManager();

    static void AddActor(GamVActor *actor);

    static GamVActor * GetActor(std::string name);

protected:
    static GamActorManager *fInstance;
    static std::vector<GamVActor *> fActors;
};

#endif // GamActorManager_h
