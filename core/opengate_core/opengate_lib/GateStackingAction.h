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
  GateStackingAction();

  ~GateStackingAction() override = default;

  void RegisterActor(GateVActor *actor, bool is_chemistry_actor = false);

  void NewStage() override;

  bool fChemistryIsActive;

protected:
  std::vector<GateVActor *> fNonChemistryStageActors;
  std::vector<GateVActor *> fChemistryStageActors;
};

#endif // GateStackingAction_h
