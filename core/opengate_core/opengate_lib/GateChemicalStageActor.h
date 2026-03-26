/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemicalStageActor_h
#define GateChemicalStageActor_h

#include "GateVChemistryActor.h"
#include <cfloat>
#include <pybind11/stl.h>
#include <map>
#include <vector>

namespace py = pybind11;

class GateChemicalStageActor : public GateVChemistryActor {

public:
  struct SpeciesEntry {
    long number{0};
    double sumG{0.0};
    double sumG2{0.0};
  };

public:
  explicit GateChemicalStageActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void StartSimulationAction() override;
  void BeginOfEventAction(const G4Event *event) override;
  void EndOfEventAction(const G4Event *event) override;
  void SteppingAction(G4Step *step) override;
  void NewStage() override;
  void StartProcessing() override;
  void UserPreTimeStepAction() override;
  void UserPostTimeStepAction() override;
  void UserReactionAction(const G4Track &trackA, const G4Track &trackB,
                          const std::vector<G4Track *> *products) override;
  void EndProcessing() override;

  long GetNumberOfKilledParticles() const { return fNbKilledParticles; }
  long GetNumberOfAbortedEvents() const { return fNbAbortedEvents; }
  long GetNumberOfChemistryStarts() const { return fNbChemistryStarts; }
  long GetNumberOfChemistryStages() const { return fNbChemistryStages; }
  long GetNumberOfPreTimeStepCalls() const { return fNbPreTimeStepCalls; }
  long GetNumberOfPostTimeStepCalls() const { return fNbPostTimeStepCalls; }
  long GetNumberOfReactions() const { return fNbReactions; }
  long GetNumberOfRecordedEvents() const { return fNbRecordedEvents; }
  double GetAccumulatedPrimaryEnergyLoss() const { return fAccumulatedELoss; }
  double GetAccumulatedEnergyDeposit() const { return fAccumulatedEdep; }
  double GetMeanRestrictedLET() const;
  double GetStdRestrictedLET() const;
  py::dict GetSpeciesInfo() const;
  py::dict GetReactionCounts() const;
  py::list GetRecordedTimes() const;

protected:
  bool ShouldApplyPrimaryLogic(const G4Track *track) const;
  void ConfigureTimesToRecordIfNeeded();
  void RecordSpeciesAtEndOfChemicalStage();
  std::string GetReactionSignature(const G4Track &trackA, const G4Track &trackB,
                                   const std::vector<G4Track *> *products) const;

  bool fTrackOnlyPrimary{true};
  int fPrimaryPDGCode{11};
  double fELossMin{-1.0};
  double fELossMax{-1.0};
  double fKineticEMin{0.0};
  G4ThreeVector fBoundingBoxSize;
  bool fUseBoundingBox{false};
  double fLETCutoff{DBL_MAX};
  std::vector<double> fTimesToRecord;
  int fNumberOfTimeBins{0};

  double fEventELoss{0.0};
  double fAccumulatedELoss{0.0};
  double fEventEdep{0.0};
  double fAccumulatedEdep{0.0};
  double fEventStepLength{0.0};
  double fEventRestrictedLET{0.0};
  int fLETTrackID{1};
  double fAccumulatedLET{0.0};
  double fAccumulatedLET2{0.0};
  long fNbKilledParticles{0};
  long fNbAbortedEvents{0};
  long fNbChemistryStarts{0};
  long fNbChemistryStages{0};
  long fNbPreTimeStepCalls{0};
  long fNbPostTimeStepCalls{0};
  long fNbReactions{0};
  long fNbRecordedEvents{0};
  std::map<double, std::map<std::string, SpeciesEntry>> fSpeciesInfoPerTime;
  std::map<std::string, long> fReactionCounts;
};

#endif // GateChemicalStageActor_h
