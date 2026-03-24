/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemicalStageActor_h
#define GateChemicalStageActor_h

#include "GateVChemistryActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateChemicalStageActor : public GateVChemistryActor {

public:
  explicit GateChemicalStageActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void StartSimulationAction() override;
  void BeginOfEventAction(const G4Event *event) override;
  void SteppingAction(G4Step *step) override;
  void NewStage() override;
  void StartProcessing() override;
  void UserPreTimeStepAction() override;
  void UserPostTimeStepAction() override;
  void EndProcessing() override;

  long GetNumberOfKilledParticles() const { return fNbKilledParticles; }
  long GetNumberOfAbortedEvents() const { return fNbAbortedEvents; }
  long GetNumberOfChemistryStarts() const { return fNbChemistryStarts; }
  long GetNumberOfPreTimeStepCalls() const { return fNbPreTimeStepCalls; }
  long GetNumberOfPostTimeStepCalls() const { return fNbPostTimeStepCalls; }
  double GetAccumulatedPrimaryEnergyLoss() const { return fAccumulatedELoss; }

protected:
  bool ShouldApplyPrimaryLogic(const G4Track *track) const;

  bool fTrackOnlyPrimary{true};
  int fPrimaryPDGCode{11};
  double fELossMin{-1.0};
  double fELossMax{-1.0};
  G4ThreeVector fBoundingBoxSize;
  bool fUseBoundingBox{false};

  double fEventELoss{0.0};
  double fAccumulatedELoss{0.0};
  long fNbKilledParticles{0};
  long fNbAbortedEvents{0};
  long fNbChemistryStarts{0};
  long fNbPreTimeStepCalls{0};
  long fNbPostTimeStepCalls{0};
};

#endif // GateChemicalStageActor_h
