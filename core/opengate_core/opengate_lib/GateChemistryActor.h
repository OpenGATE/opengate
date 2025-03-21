/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemistryActor_h
#define GateChemistryActor_h

#include <G4MolecularConfiguration.hh>
#include <G4Scheduler.hh>
#include <G4Track.hh>
#include <G4UserTimeStepAction.hh>
#include <pybind11/detail/common.h>
#include <set>
#include <vector>

#include "GateVActor.h"

class G4EmCalculator;
class G4HCofThisEvent;
class G4H2O;

class GateVChemistryActor : public GateVActor {
public:
  using Tracks = std::vector<G4Track *>;

public:
  using GateVActor::GateVActor;

  virtual void UserReactionAction(G4Track const &, G4Track const &,
                                  Tracks const &) = 0;
};

class TimeStepAction : public G4UserTimeStepAction {
public:
  void UserReactionAction(const G4Track &, const G4Track &,
                          const std::vector<G4Track *> *) override;

  void addChemistryActor(GateVChemistryActor &actor) {
    _chemistryActors.push_back(&actor);
  }

private:
  std::vector<GateVChemistryActor *> _chemistryActors;
};

class GateChemistryActor : public GateVChemistryActor {
public:
  // Constructor
  GateChemistryActor(pybind11::dict &user_info);

  void InitializeUserInfo(pybind11::dict &user_info) override;

  void InitializeG4PreInitState() override;

  void InitializeCpp() override;

  void Initialize(G4HCofThisEvent *hce) override;

  void EndSimulationAction() override;
  void EndOfRunAction(const G4Run *event) override;
  void EndOfEventAction(const G4Event *event) override;
  void SteppingAction(G4Step *step) override;
  void NewStage() override;

  void UserReactionAction(G4Track const &, G4Track const &,
                          Tracks const &) override;

  void setTimeBinsCount(int);

  [[nodiscard]] pybind11::list getTimes() const;
  [[nodiscard]] pybind11::dict getData() const;
  [[nodiscard]] pybind11::dict getReactions() const;

public:
  struct ReactionInput {
    std::vector<std::string> reactants;
    std::vector<std::string> products;
    std::string fix;
    double rate;
    int type;
  };

  using ReactionInputs = std::vector<ReactionInput>;

  struct SpeciesInfo {
    int count = 0;
    double g = 0.;
    double sqG = 0.;
  };

  using SpeciesName = std::string;
  using InnerSpeciesMap = std::map<double, SpeciesInfo>;
  using SpeciesMap = std::map<SpeciesName, InnerSpeciesMap>;

  using Products = std::vector<std::string>;
  using Reaction = std::tuple<std::string, std::string, Products>;
  using Reactions = std::vector<Reaction>;
  using ReactionsMap = std::map<double, Reactions>;

protected:
  static ReactionInputs getReactionInputs(pybind11::dict &user_info,
                                          std::string const &key);
  void setupConstructReactionTableHook();

private:
  G4H2O *_g4H2O;
  TimeStepAction _timeStepAction;

  SpeciesMap _speciesInfoPerTime;
  ReactionsMap _reactionsPerTime;

  double _edepSum = 0;
  double _edepSumRun = 0;
  unsigned _nbEvents = 0;
  std::set<double> _timesToRecord;

  int _moleculeCounterVerbose = 0;
  std::string _timeStepModelStr = "IRT";
  double _endTime;
  bool _keepDefaultReactions = true;
  std::vector<ReactionInput> _reactions;
};

#endif
