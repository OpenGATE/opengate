/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemicalStageActor_h
#define GateChemicalStageActor_h

#include "GateVChemistryActor.h"
#include <array>
#include <cfloat>
#include <map>
#include <pybind11/stl.h>
#include <string>
#include <vector>

namespace py = pybind11;

class GateChemicalStageActor : public GateVChemistryActor {

public:
  struct SpeciesEntry {
    long number{0};
    double sumG{0.0};
    double sumG2{0.0};
  };

  struct TrackedReactionRecord {
    std::string name;
    std::array<std::string, 2> reactants;
    std::vector<std::string> products;
    bool recordTimeSeries{true};
    long totalCount{0};
    std::vector<double> times{0.0};
    std::vector<long> counts{0};

    void Reset() {
      totalCount = 0;
      times = {0.0};
      counts = {0};
    }
  };

  struct TrackedSpeciesRecord {
    std::string name;
    std::string runtimeName;
    bool recordTimeSeries{true};
    long totalCount{0};
    std::vector<double> times{0.0};
    std::vector<long> counts{0};

    void Reset() {
      totalCount = 0;
      times = {0.0};
      counts = {0};
    }
  };

public:
  explicit GateChemicalStageActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void StartSimulationAction() override;
  void BeginOfEventAction(const G4Event *event) override;
  void EndOfEventAction(const G4Event *event) override;
  void SteppingAction(G4Step *step) override;
  void NewStage() override;
  void StartChemistryTracking(G4Track *track) override;
  void StartChemistryProcessing() override;
  void PreChemistryTimeStepAction() override;
  void PostChemistryTimeStepAction() override;
  void ChemistryReactionAction(const G4Track &trackA, const G4Track &trackB,
                               const std::vector<G4Track *> *products) override;
  void EndChemistryProcessing() override;

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
  py::list GetRecordedTimes() const;
  void SetMoleculeCounterId(G4int id) { fMoleculeCounterId = id; }
  void RegisterConfiguredReactionCounter(const std::string &counterName,
                                         const py::list &trackedReactions,
                                         bool recordTimeSeries);
  py::dict GetConfiguredReactionCounterResults(
      const std::string &counterName) const;
  void RegisterConfiguredSpeciesCounter(const std::string &counterName,
                                        const py::list &trackedSpecies,
                                        bool recordTimeSeries);
  py::dict GetConfiguredSpeciesCounterResults(
      const std::string &counterName) const;

protected:
  bool ShouldApplyPrimaryLogic(const G4Track *track) const;
  void ConfigureTimesToRecordIfNeeded();
  void RecordSpeciesAtEndOfChemicalStage();
  static std::array<std::string, 2>
  CanonicalizeReactants(const std::string &reactantA,
                        const std::string &reactantB);
  static std::vector<std::string>
  CanonicalizeProducts(const std::vector<std::string> &products);
  static std::string ResolveRuntimeMoleculeName(const G4Track &track);
  static std::string StripChargeSuffix(const std::string &moleculeName);

  bool fTrackOnlyPrimary{true};
  int fPrimaryPDGCode{11};
  double fELossMin{-1.0};
  double fELossMax{-1.0};
  double fKineticEMin{0.0};
  double fLETCutoff{DBL_MAX};
  std::vector<double> fTimesToRecord;
  int fNumberOfTimeBins{0};
  G4int fMoleculeCounterId{-1};

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
  std::map<std::string, std::vector<TrackedReactionRecord>>
      fConfiguredReactionCounters;
  std::map<std::string, std::vector<TrackedSpeciesRecord>>
      fConfiguredSpeciesCounters;
};

#endif // GateChemicalStageActor_h
