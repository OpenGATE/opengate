/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateChemistryActor.h"

#include <CLHEP/Units/SystemOfUnits.h>
#include <G4DNAChemistryManager.hh>
#include <G4DNAMolecularReactionTable.hh>
#include <G4EmDNAChemistry_option3.hh>
#include <G4EmDNAPhysics_option3.hh>
#include <G4EmParameters.hh>
#include <G4EventManager.hh>
#include <G4H2O.hh>
#include <G4MoleculeCounter.hh>
#include <G4RunManager.hh>
#include <G4Scheduler.hh>
#include <G4THitsMap.hh>
#include <G4UnitsTable.hh>
#include <G4ios.hh>
#include <pybind11/pybind11.h>
#include <pybind11/pytypes.h>

#include "GateHelpers.h"
#include "GateHelpersDict.h"

#include "../g4_bindings/chemistryadaptator.h"
#include "GateVActor.h"

GateChemistryActor::GateChemistryActor(pybind11::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("NewStage");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndSimulationAction");

  _timeStepModelStr = DictGetStr(user_info, "timestep_model");
  _endTime = DictGetDouble(user_info, "end_time");
  _reactions = getReactionInputs(user_info, "reactions");
  _keepDefaultReactions = DictGetBool(user_info, "default_reactions");
  _moleculeCounterVerbose = DictGetInt(user_info, "molecule_counter_verbose");

  setTimeBinsCount(DictGetInt(user_info, "time_bins_count"));

  G4MoleculeCounter::Instance()->SetVerbose(_moleculeCounterVerbose);
  G4MoleculeCounter::Instance()->Use();
  G4MoleculeCounter::Instance()->DontRegister(G4H2O::Definition());
  G4MolecularConfiguration::PrintAll();

  auto timeStepModel = fIRT;
  if (_timeStepModelStr == "IRT")
    timeStepModel = fIRT;
  else if (_timeStepModelStr == "SBS")
    timeStepModel = fSBS;
  else if (_timeStepModelStr == "IRT_syn")
    timeStepModel = fIRT_syn;
  else /* TODO error; detect Python-side? */
    ;

  G4Scheduler::Instance()->SetEndTime(_endTime);

  if (!_reactions.empty())
    setupConstructReactionTableHook();
  else if (!_keepDefaultReactions)
    Fatal("Disabling default reactions requires to provide reactions");

  auto *chemistryList =
      ChemistryAdaptator<G4EmDNAChemistry_option3>::getChemistryList();
  if (chemistryList != nullptr)
    chemistryList->SetTimeStepModel(timeStepModel);
}

void GateChemistryActor::Initialize(G4HCofThisEvent *hce) {
  GateVActor::Initialize(hce);

  G4MoleculeCounter::Instance()->ResetCounter();
  G4DNAChemistryManager::Instance()->ResetCounterWhenRunEnds(false);
}

void GateChemistryActor::EndSimulationAction() {}

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
        auto &speciesInfo = _speciesInfoPerTime[molecule];

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

pybind11::list GateChemistryActor::getTimes() const {
  pybind11::list o;
  std::for_each(std::begin(_timesToRecord), std::end(_timesToRecord),
                [&o](auto const &v) { o.append(v); });
  return o;
}

pybind11::dict GateChemistryActor::getData() const {
  pybind11::dict o;
  for (auto const &[molecule, map] : _speciesInfoPerTime) {
    pybind11::dict dMolecule;
    auto const *name = molecule->GetName().c_str();

    py::list count;
    py::list g;
    py::list sqG;

    for (auto const &[time, data] :
         map) { // time order is guaranteed by std::map
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

GateChemistryActor::ReactionInputs
GateChemistryActor::getReactionInputs(pybind11::dict &user_info,
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
