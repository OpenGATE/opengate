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

template<typename T> std::vector<T*> GetActorsFromActorInheritanceDiagram()
   {
        static_assert(std::is_base_of_v<GateVActor, T>,
                      "T must derive from GateVActor");

        std::vector<T*> result;
        result.reserve(fActors.size());

        for (auto* a : fActors) {
            if (auto* p = dynamic_cast<T*>(a)) {
                result.push_back(p);
            }
        }
        return result;
    }

protected:
  static GateActorManager *fInstance;
  static std::vector<GateVActor *> fActors;
};

#endif // GateActorManager_h
