/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemistryLongTimeActor_h
#define GateChemistryLongTimeActor_h

#include <G4MolecularConfiguration.hh>
#include <G4VChemistryWorld.hh>
#include <memory>
#include <pybind11/detail/common.h>
#include <set>
#include <vector>

#include "GateVActor.h"

class G4EmCalculator;
class G4HCofThisEvent;

class GateChemistryLongTimeActor : public GateVActor {
public:
  GateChemistryLongTimeActor(pybind11::dict &user_info);

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
  struct ScavengerConfig {
    std::string species;
    double concentration;
    std::string unit;
  };

  using ScavengerConfigs = std::vector<ScavengerConfig>;

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

private:
  class ChemistryWorld : public G4VChemistryWorld {
  public:
    ChemistryWorld(GateChemistryLongTimeActor *actor);

    void ConstructChemistryBoundary() override;
    void ConstructChemistryComponents() override;

  private:
    GateChemistryLongTimeActor *_actor;
  };

protected:
  static ScavengerConfigs getScavengerConfigs(pybind11::dict &user_info,
                                              std::string const &key);

  static ReactionInputs getReactionInputs(pybind11::dict &user_info,
                                          std::string const &key);

private:
  SpeciesMap _speciesInfoPerTime;

  double _edepSum = 0;
  double _edepSumRun = 0;
  unsigned _nbEvents = 0;
  std::set<double> _timesToRecord;

  int _moleculeCounterVerbose = 0;
  std::string _timeStepModelStr = "SBS";
  double _endTime;
  std::vector<ReactionInput> _reactions;

  std::unique_ptr<G4VChemistryWorld> _chemistryWorld;

  double _pH = 7;
  ScavengerConfigs _scavengerConfigs;

  double _doseCutOff = 0;

  bool _resetScavengerForEachBeam = false;

  // TODO remove
  std::vector<double> _boundarySize;
};

#endif
