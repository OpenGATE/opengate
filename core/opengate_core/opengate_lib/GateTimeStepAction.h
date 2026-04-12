/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTimeStepAction_h
#define GateTimeStepAction_h

#include "G4UserTimeStepAction.hh"
#include "GateVChemistryActor.h"

class GateTimeStepAction : public G4UserTimeStepAction {

public:
  GateTimeStepAction();

  ~GateTimeStepAction() override = default;

  void RegisterActor(GateVChemistryActor *actor);

  void StartProcessing() override;
  void NewStage() override;
  void UserPreTimeStepAction() override;
  void UserPostTimeStepAction() override;
  void UserReactionAction(const G4Track &trackA, const G4Track &trackB,
                          const std::vector<G4Track *> *products) override;
  void EndProcessing() override;

protected:
  std::vector<GateVChemistryActor *> fStartChemistryProcessingActors;
  std::vector<GateVChemistryActor *> fNewStageActors;
  std::vector<GateVChemistryActor *> fPreChemistryTimeStepActors;
  std::vector<GateVChemistryActor *> fPostChemistryTimeStepActors;
  std::vector<GateVChemistryActor *> fChemistryReactionActors;
  std::vector<GateVChemistryActor *> fEndChemistryProcessingActors;
};

#endif // GateTimeStepAction_h
