/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemistryActor_h
#define GateChemistryActor_h

#include <G4MolecularConfiguration.hh>
#include <pybind11/detail/common.h>
#include <set>
#include <vector>

#include "GateVActor.h"

class G4EmCalculator;
class G4HCofThisEvent;

class GateChemistryActor : public GateVActor {
public:
  // Constructor
  GateChemistryActor(pybind11::dict &user_info);

  void Initialize(G4HCofThisEvent *hce) override;

  void EndSimulationAction() override;
  void EndOfRunAction(const G4Run *event) override;
  void EndOfEventAction(const G4Event *event) override;
  void SteppingAction(G4Step *step) override;
  void NewStage() override;

  void setTimeBinsCount(int);

  [[nodiscard]] pybind11::list getTimes() const;
  [[nodiscard]] pybind11::dict getData() const;

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

  using SpeciesPtr = G4MolecularConfiguration const *;
  using InnerSpeciesMap = std::map<double, SpeciesInfo>;
  using SpeciesMap = std::map<SpeciesPtr, InnerSpeciesMap>;

protected:
  static ReactionInputs getReactionInputs(pybind11::dict &user_info,
                                          std::string const &key);
  void setupConstructReactionTableHook();

private:
  SpeciesMap _speciesInfoPerTime;

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
