/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateRunAction_h
#define GateRunAction_h

#include "G4Event.hh"
#include "G4UserRunAction.hh"
#include "GateSourceManager.h"
#include "GateVActor.h"

class GateRunAction : public G4UserRunAction {

public:
  GateRunAction(GateSourceManager *sm);

  virtual ~GateRunAction() {}

  void RegisterActor(GateVActor *actor);

  virtual void BeginOfRunAction(const G4Run *run);

  virtual void EndOfRunAction(const G4Run *run);

protected:
  GateSourceManager *fSourceManager;
  std::vector<GateVActor *> fBeginOfRunAction_actors;
  std::vector<GateVActor *> fEndOfRunAction_actors;
  std::vector<GateVActor *> fEndOfSimulationWorkerAction_actors;
};

#endif // GateRunAction_h
