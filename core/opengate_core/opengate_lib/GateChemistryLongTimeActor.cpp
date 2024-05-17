/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateChemistryLongTimeActor.h"

#include <CLHEP/Units/SystemOfUnits.h>
#include <G4DNABoundingBox.hh>
#include <G4DNAChemistryManager.hh>
#include <G4DNAMolecularReactionTable.hh>
#include <G4EmDNAChemistry_option3.hh>
#include <G4EmDNAPhysics_option3.hh>
#include <G4EmParameters.hh>
#include <G4EventManager.hh>
#include <G4H2O.hh>
#include <G4MoleculeCounter.hh>
#include <G4MoleculeTable.hh>
#include <G4RunManager.hh>
#include <G4Scheduler.hh>
#include <G4THitsMap.hh>
#include <G4Track.hh>
#include <G4TrackStatus.hh>
#include <G4UnitsTable.hh>
#include <G4VChemistryWorld.hh>
#include <G4ios.hh>
#include <initializer_list>
#include <memory>
#include <pybind11/pybind11.h>
#include <pybind11/pytypes.h>

#include "GateHelpersDict.h"
#include <string>
#include <vector>

#include "../g4_bindings/chemistryadaptator.h"
#include "GateVActor.h"

GateChemistryLongTimeActor::ChemistryWorld::ChemistryWorld(
    GateChemistryLongTimeActor *actor)
    : _actor(actor) {}

void GateChemistryLongTimeActor::ChemistryWorld::ConstructChemistryBoundary() {
  auto const &size = _actor->_boundarySize;
  std::initializer_list<double> boundingBox{
      // high, low
      size[0], -size[0], // x
      size[1], -size[1], // y
      size[2], -size[2]  // z
  };
  fpChemistryBoundary = std::make_unique<G4DNABoundingBox>(boundingBox);
}

void GateChemistryLongTimeActor::ChemistryWorld::
    ConstructChemistryComponents() {
  constexpr auto water = 55.3; // from NIST material database
  constexpr auto moleLiter = CLHEP::mole * CLHEP::liter;

  constexpr double pKw = 14; // at 25°C pK of water is 14
  auto const &pH = _actor->_pH;

  auto *moleculeTable = G4MoleculeTable::Instance();

  auto *mH2O = moleculeTable->GetConfiguration("H2O");
  fpChemicalComponent[mH2O] = water / moleLiter;

  auto *mH3Op = moleculeTable->GetConfiguration("H3Op(B)");
  fpChemicalComponent[mH3Op] = std::pow(10, -pH) / moleLiter; // pH = 7

  auto *mOHm = moleculeTable->GetConfiguration("OHm(B)");
  fpChemicalComponent[mOHm] = std::pow(10, -(pKw - pH)) / moleLiter; // pH = 7

  auto *mO2 = moleculeTable->GetConfiguration("O2");
  fpChemicalComponent[mO2] = (0. / 100) * 0.0013 / moleLiter;

  // apply scavanger configurations
  for (auto const &scavengerConfig : _actor->_scavengerConfigs) {
    auto *m = moleculeTable->GetConfiguration(scavengerConfig.species);
    auto const &concentration = scavengerConfig.concentration;
    auto const &unitWithPrefix = scavengerConfig.unit;
    if (not unitWithPrefix.empty()) {
      char unit = *unitWithPrefix.rbegin();
      if (unit == 'M') {
        double factor = 1;
        if (unitWithPrefix.size() > 1) {
          auto prefix = unitWithPrefix.substr(0, unitWithPrefix.size() - 1);
          if (prefix == "u")
            factor = 1e-6;
          else if (prefix == "m")
            factor = 1e-3;
          else // TODO error
            ;
        }

        fpChemicalComponent[m] = factor * concentration / moleLiter;
      } else if (unit == '%') {
        constexpr auto o2 = 0.0013;
        double concentrationInM = fpChemicalComponent[m] =
            (concentration / 100) * o2 / moleLiter;
      }
    }
  }
}

/* *** */

GateChemistryLongTimeActor::GateChemistryLongTimeActor(
    pybind11::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("NewStage");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndSimulationAction");

  _timeStepModelStr = DictGetStr(user_info, "timestep_model");
  _endTime = DictGetDouble(user_info, "end_time");
  _reactions = getReactionInputs(user_info, "reactions");
  _moleculeCounterVerbose = DictGetInt(user_info, "molecule_counter_verbose");

  setTimeBinsCount(DictGetInt(user_info, "time_bins_count"));

  _pH = DictGetDouble(user_info, "pH");
  _scavengerConfigs = getScavengerConfigs(user_info, "scavengers");

  _doseCutOff = DictGetDouble(user_info, "dose_cutoff");

  _resetScavengerForEachBeam =
      DictGetBool(user_info, "reset_scavenger_for_each_beam");

  // TODO remove
  _boundarySize = DictGetVecDouble(user_info, "boundary_size");
}

void GateChemistryLongTimeActor::Initialize(G4HCofThisEvent *hce) {
  GateVActor::Initialize(hce);

  _chemistryWorld = std::make_unique<ChemistryWorld>(this);
  _chemistryWorld->ConstructChemistryComponents();

  G4Scheduler::Instance()->ResetScavenger(_resetScavengerForEachBeam);

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

  {
    auto constructReactionTable =
        [&reactions = _reactions](G4DNAMolecularReactionTable *reactionTable) {
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

  auto *chemistryList =
      ChemistryAdaptator<G4EmDNAChemistry_option3>::getChemistryList();
  if (chemistryList != nullptr)
    chemistryList->SetTimeStepModel(timeStepModel);

  G4MoleculeCounter::Instance()->ResetCounter();
  G4DNAChemistryManager::Instance()->ResetCounterWhenRunEnds(false);

  G4MoleculeCounter::Instance()->ResetCounter();
}

void GateChemistryLongTimeActor::EndSimulationAction() {}

void GateChemistryLongTimeActor::EndOfRunAction(G4Run const *) {
  for (auto &[molecule, map] : _speciesInfoPerTime) {
    for (auto &[time, data] : map) {
      data.g /= _nbEvents;   // mean value of g
      data.sqG /= _nbEvents; // mean value of g²(TODO?)
    }
  }
}

void GateChemistryLongTimeActor::EndOfEventAction(G4Event const *) {
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
      G4cout << "[GateChemistryLongTimeActor] No molecule recorded, edep = "
             << G4BestUnit(_edepSum, "Energy") << G4endl;
  }

  ++_nbEvents;
  _edepSumRun += _edepSum;
  _edepSum = 0.;
  moleculeCounter->ResetCounter();
}

void GateChemistryLongTimeActor::SteppingAction(G4Step *step) {
  auto edep = step->GetTotalEnergyDeposit();
  if (edep <= 0.)
    return;

  edep *= step->GetPreStepPoint()->GetWeight();
  _edepSum += edep;

  auto *track = step->GetTrack();

  if (track->GetParentID() == 0 && track->GetCurrentStepNumber() == 1) {
    constexpr auto density = .001;
    auto volume = _chemistryWorld->GetChemistryBoundary()->Volume();
    double dose = (_edepSum / CLHEP::eV) / (density * volume * 6.242e+18);
    if (dose > _doseCutOff) {
      auto *eventManager = G4EventManager::GetEventManager();
      auto *primary = eventManager->GetConstCurrentEvent()
                          ->GetPrimaryVertex()
                          ->GetPrimary();
      auto const &name = primary->GetParticleDefinition()->GetParticleName();
      auto energy = primary->GetKineticEnergy();
      G4cout << "[GateChemistryLongTimeActor] stop beam line '" << name << "' ("
             << energy << " MeV) at dose: " << dose << " Gy" << G4endl;

      track->SetTrackStatus(fStopAndKill);
      auto const *secondaries = track->GetStep()->GetSecondaryInCurrentStep();
      for (auto const *secondary : *secondaries) {
        if (secondary != nullptr) {
          // FIXME
          // from UHDR example
          // must find how to get non-const access to secondaries
          auto *secondaryMut = const_cast<G4Track *>(secondary);
          secondaryMut->SetTrackStatus(fStopAndKill);
        }
      }
      eventManager->GetStackManager()->ClearUrgentStack();
    }
  }
}

void GateChemistryLongTimeActor::NewStage() {
  auto *stackManager = G4EventManager::GetEventManager()->GetStackManager();
  if (stackManager != nullptr && stackManager->GetNTotalTrack() == 0) {
    G4DNAChemistryManager::Instance()->Run();
  }
}

void GateChemistryLongTimeActor::setTimeBinsCount(int n) {
  double timeMin = 1 * CLHEP::ps;
  double timeMax = G4Scheduler::Instance()->GetEndTime() - 1 * CLHEP::ps;
  double timeMinLog = std::log10(timeMin);
  double timeMaxLog = std::log10(timeMax);
  double timeStepLog = (timeMaxLog - timeMinLog) / (n - 1);

  _timesToRecord.clear();
  for (int i = 0; i < n; ++i)
    _timesToRecord.insert(std::pow(10, timeMinLog + i * timeStepLog));
}

pybind11::list GateChemistryLongTimeActor::getTimes() const {
  pybind11::list o;
  std::for_each(std::begin(_timesToRecord), std::end(_timesToRecord),
                [&o](auto const &v) { o.append(v); });
  return o;
}

pybind11::dict GateChemistryLongTimeActor::getData() const {
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

GateChemistryLongTimeActor::ScavengerConfigs
GateChemistryLongTimeActor::getScavengerConfigs(pybind11::dict &user_info,
                                                std::string const &key) {
  ScavengerConfigs scavengerConfigs;

  auto configs = DictGetVecList(user_info, key);
  for (auto const &config : configs) {
    ScavengerConfig scavengerConfig;

    scavengerConfig.species = config[0].cast<std::string>();
    scavengerConfig.concentration = config[1].cast<double>();
    scavengerConfig.unit = config[2].cast<std::string>();
  }

  return scavengerConfigs;
}

GateChemistryLongTimeActor::ReactionInputs
GateChemistryLongTimeActor::getReactionInputs(pybind11::dict &user_info,
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
