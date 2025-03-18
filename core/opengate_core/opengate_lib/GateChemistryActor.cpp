/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateChemistryActor.h"

#include <CLHEP/Units/SystemOfUnits.h>
#include <G4ChemTimeStepModel.hh>
#include <G4DNAChemistryManager.hh>
#include <G4DNAMolecularReactionTable.hh>
#include <G4EmDNAChemistry_option3.hh>
#include <G4EmDNAPhysics_option3.hh>
#include <G4EmParameters.hh>
#include <G4EventManager.hh>
#include <G4H2O.hh>
#include <G4IT.hh>
#include <G4MoleculeCounter.hh>
#include <G4RunManager.hh>
#include <G4Scheduler.hh>
#include <G4StateManager.hh>
#include <G4THitsMap.hh>
#include <G4Track.hh>
#include <G4UnitsTable.hh>
#include <G4ios.hh>
#include <pybind11/pybind11.h>
#include <pybind11/pytypes.h>
#include <templates.hh>

#include "GateHelpers.h"
#include "GateHelpersDict.h"

#include "../g4_bindings/chemistryadaptator.h"
#include "GateVActor.h"
#include "pybind11/tests/pybind11_tests.h"

void TimeStepAction::UserReactionAction(
    const G4Track &a, const G4Track &b,
    const std::vector<G4Track *> *products) {
  GateChemistryActor::Tracks noProducts;
  auto &rProducts = (products ? *products : noProducts);
  for (auto &actors : _chemistryActors)
    actors->UserReactionAction(a, b, rProducts);
}

/*
 * constructors are run in G4 PreInit state
 * particle definitions must be done there
 * TODO too early
 */
GateChemistryActor::GateChemistryActor(py::dict &user_info)
    : GateVChemistryActor(user_info, false) {
  G4Scheduler::Instance()->SetUserAction(&_timeStepAction);
  _timeStepAction.addChemistryActor(*this);
}

void GateChemistryActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);

  _timeStepModelStr = DictGetStr(user_info, "timestep_model");
  _endTime = DictGetDouble(user_info, "end_time");
  _reactions = getReactionInputs(user_info, "reactions");
  _keepDefaultReactions = DictGetBool(user_info, "default_reactions");
  _moleculeCounterVerbose = DictGetInt(user_info, "molecule_counter_verbose");

  setTimeBinsCount(DictGetInt(user_info, "time_bins_count"));
}

void GateChemistryActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  G4MoleculeCounter::Instance()->SetVerbose(_moleculeCounterVerbose);
  G4MoleculeCounter::Instance()->Use();
  // G4MoleculeCounter::Instance()->DontRegister(_g4H2O);
  G4MolecularConfiguration::PrintAll();
  G4MoleculeCounter::Instance()->CheckTimeForConsistency(false);

  auto timeStepModel = G4ChemTimeStepModel::Unknown;
  if (_timeStepModelStr == "IRT")
    timeStepModel = G4ChemTimeStepModel::IRT;
  else if (_timeStepModelStr == "SBS")
    timeStepModel = G4ChemTimeStepModel::SBS;
  else if (_timeStepModelStr == "IRT_syn")
    timeStepModel = G4ChemTimeStepModel::IRT_syn;
  else /* TODO error; detect Python-side? */
    ;

  G4Scheduler::Instance()->SetEndTime(_endTime);

  if (!_reactions.empty())
    setupConstructReactionTableHook();
  else if (!_keepDefaultReactions)
    Fatal("Disabling default reactions requires to provide reactions");

  G4EmParameters::Instance()->SetTimeStepModel(timeStepModel);
}

void GateChemistryActor::Initialize(G4HCofThisEvent *hce) {
  GateVActor::Initialize(hce);

  G4MoleculeCounter::Instance()->ResetCounter();
  G4DNAChemistryManager::Instance()->ResetCounterWhenRunEnds(false);
}

void GateChemistryActor::EndSimulationAction() {
  G4cout << "[GateChemistryActor] EndSimulationAction edep = "
         << G4BestUnit(_edepSumRun, "Energy") << G4endl;
}

void GateChemistryActor::EndOfRunAction(G4Run const *) {
  for (auto &[molecule, map] : _speciesInfoPerTime) {
    for (auto &[time, data] : map) {
      data.g /= _nbEvents;   // mean value of g
      data.sqG /= _nbEvents; // mean value of g²(TODO?)
    }
  }
}

void GateChemistryActor::EndOfEventAction(G4Event const *) {
  auto *moleculeCounter = G4MoleculeCounter::Instance();

  if (not G4EventManager::GetEventManager()
              ->GetConstCurrentEvent()
              ->IsAborted()) {
    auto species = moleculeCounter->GetRecordedMolecules();
    if (species && !species->empty()) {
      for (auto const *molecule : *species) {
        auto speciesName = molecule->GetName();
        auto &speciesInfo = _speciesInfoPerTime[speciesName];

        for (auto time : _timesToRecord) {
          auto nbMol = moleculeCounter->GetNMoleculesAtTime(molecule, time);

          if (nbMol < 0) {
            G4cerr << "Invalid molecule count: " << nbMol << " < 0 " << G4endl;
            G4Exception("", "N < 0", FatalException, "");
          }

          double gValue = (nbMol / (_edepSum / CLHEP::eV)) * 100.;

          auto &molInfo = speciesInfo[time];
          molInfo.count += nbMol;
          molInfo.g += gValue;
          molInfo.sqG += gValue * gValue;
        }
      }
    } else
      G4cout << "[GateChemistryActor] No molecule recorded, edep = "
             << G4BestUnit(_edepSum, "Energy") << G4endl;
  }

  ++_nbEvents;
  _edepSumRun += _edepSum;
  _edepSum = 0.;
  moleculeCounter->ResetCounter();
}

void GateChemistryActor::SteppingAction(G4Step *step) {
  auto edep = step->GetTotalEnergyDeposit();
  if (edep <= 0.)
    return;

  edep *= step->GetPreStepPoint()->GetWeight();
  _edepSum += edep;
}

void GateChemistryActor::NewStage() {
  auto *stackManager = G4EventManager::GetEventManager()->GetStackManager();
  if (stackManager != nullptr && stackManager->GetNTotalTrack() == 0) {
    G4DNAChemistryManager::Instance()->Run();
  }
}

void GateChemistryActor::UserReactionAction(G4Track const &a, G4Track const &b,
                                            Tracks const &rs) {
  auto globalTime = G4Scheduler::Instance()->GetGlobalTime();

  static auto nameFromTrack = [](G4Track const *track) {
    auto *it = GetIT(*track);
    return it->GetName();
  };

  auto nameA = nameFromTrack(&a);
  auto nameB = nameFromTrack(&b);

  Products products(rs.size());
  std::transform(std::begin(rs), std::end(rs), std::begin(products),
                 nameFromTrack);

  _reactionsPerTime[globalTime].emplace_back(nameA, nameB, products);
}

void GateChemistryActor::setTimeBinsCount(int n) {
  double timeMin = 1 * CLHEP::ps;
  double timeMax = G4Scheduler::Instance()->GetEndTime() - 1 * CLHEP::ps;
  double timeMinLog = std::log10(timeMin);
  double timeMaxLog = std::log10(timeMax);
  double timeStepLog = (timeMaxLog - timeMinLog) / (n - 1);

  _timesToRecord.clear();
  for (int i = 0; i < n; ++i)
    _timesToRecord.insert(std::pow(10, timeMinLog + i * timeStepLog));
}

py::list GateChemistryActor::getTimes() const {
  py::list o;
  std::for_each(std::begin(_timesToRecord), std::end(_timesToRecord),
                [&o](auto const &v) { o.append(v); });
  return o;
}

py::dict GateChemistryActor::getData() const {
  py::dict o;
  for (auto const &[molecule, map] : _speciesInfoPerTime) {
    py::dict dMolecule;
    auto const *name = molecule.c_str();

    py::list count;
    py::list g;
    py::list sqG;

    // time order is guaranteed by std::map
    for (auto const &[time, data] : map) {
      count.append(data.count);
      g.append(data.g);
      sqG.append(data.sqG);
    }

    if (not o.contains(name)) {
      dMolecule["count"] = count;
      dMolecule["g"] = g;
      dMolecule["sqG"] = sqG;

      o[name] = dMolecule;
    }
  }

  return o;
}

py::dict GateChemistryActor::getReactions() const {
  py::dict o;
  for (auto const &[time, reactions] : _reactionsPerTime) {
    py::list lReactions;

    for (auto const &[a, b, products] : reactions) {
      py::dict dReaction;
      py::list reactants;

      reactants.append(a);
      reactants.append(b);

      dReaction["reactants"] = reactants;
      dReaction["products"] = products;

      lReactions.append(dReaction);
    }

    o[py::float_{time}] = lReactions;
  }

  return o;
}

GateChemistryActor::ReactionInputs
GateChemistryActor::getReactionInputs(py::dict &user_info,
                                      std::string const &key) {
  ReactionInputs reactionInputs;

  auto reactions = DictGetVecList(user_info, key);
  for (auto const &reaction : reactions) {
    ReactionInput reactionInput;

    reactionInput.reactants = reaction[0].cast<std::vector<std::string>>();
    reactionInput.products = reaction[1].cast<std::vector<std::string>>();
    reactionInput.fix = reaction[2].cast<std::string>();
    reactionInput.rate = reaction[3].cast<double>();
    reactionInput.type = reaction[4].cast<int>();

    reactionInputs.push_back(reactionInput);
  }

  return reactionInputs;
}

void GateChemistryActor::setupConstructReactionTableHook() {
  auto constructReactionTable =
      [&reactions = _reactions, &keepDefaultReactions = _keepDefaultReactions](
          G4DNAMolecularReactionTable *reactionTable) {
        if (!keepDefaultReactions)
          reactionTable->Reset();

        for (auto const &reaction : reactions) {
          double rate =
              reaction.rate * (1e-3 * CLHEP::m3 / (CLHEP::mole * CLHEP::s));
          auto *reactionData = new G4DNAMolecularReactionData(
              rate, reaction.reactants[0], reaction.reactants[1]);
          for (auto const &product : reaction.products)
            if (product != "H2O")
              reactionData->AddProduct(product);
          reactionData->ComputeEffectiveRadius();
          reactionData->SetReactionType(reaction.type);

          reactionTable->SetReaction(reactionData);
        }

        reactionTable->PrintTable();
      };

  ChemistryAdaptator<G4EmDNAChemistry_option3>::setConstructReactionTableHook(
      constructReactionTable);
}
