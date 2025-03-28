/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateActorManager_h
#define GateActorManager_h

#include "GateVActor.h"

class GateActorManager {
public:
  static GateActorManager *GetInstance();

  virtual ~GateActorManager();

  static void AddActor(GateVActor *actor);

  static GateVActor *GetActor(const std::string &name);

protected:
  static GateActorManager *fInstance;
  static std::vector<GateVActor *> fActors;
};

#endif // GateActorManager_h
