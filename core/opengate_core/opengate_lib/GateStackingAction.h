/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateStackingAction_h
#define GateStackingAction_h

#include "G4UserStackingAction.hh"
#include "GateVActor.h"

class GateStackingAction : public G4UserStackingAction {

public:
  GateStackingAction() = default;

  ~GateStackingAction() override = default;

  void RegisterActor(GateVActor *actor);

  void NewStage() override;

  auto *stackManager() { return G4UserStackingAction::stackManager; }

protected:
  std::vector<GateVActor *> fNewStageActors;
};

#endif // GateTrackingAction_h
