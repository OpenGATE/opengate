/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePositroniumSource.h"
#include "G4IonTable.hh"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "fmt/core.h"
#include <G4UnitsTable.hh>
#include <algorithm>
#include <iterator>
#include <locale>
#include <numeric>

#include "GatePositroniumDecayModel.h"
#include "GatePositroniumDecayModelParams.h"

GatePositroniumSource::GatePositroniumSource() : GateGenericSource() {
}

GatePositroniumSource::~GatePositroniumSource() = default;

void GatePositroniumSource::InitializeUserInfo(py::dict &user_info) {
  GateGenericSource::InitializeUserInfo(user_info);

  auto positronium_fractions = DictGetVecDouble(user_info, "positronium_fractions");
  auto positronium_lifetimes = DictGetVecDouble(user_info,"positronium_lifetimes");
  auto decay_kinds = DictGetVecStr(user_info,"decay_kinds");
  auto prompt_photon_probabilities = DictGetVecDouble(user_info,"prompt_photon_probabilities");
  auto prompt_photon_energies = DictGetVecDouble(user_info,"prompt_photon_energies");

  PositroniumDecayModelParams params;
  params.fFractions = positronium_fractions;
  params.fLifetimes = positronium_lifetimes;
  params.fDecayKind = ParsePositroniumDecayKind(decay_kinds);
  params.fPromptGammaProbabilities = prompt_photon_probabilities;
  params.fPromptGammaEnergy = prompt_photon_energies;

  pModel = std::make_unique<GatePositroniumDecayModel>(params);
}

std::vector<PositroniumDecayKind> GatePositroniumSource::ParsePositroniumDecayKind(const std::vector<string> & decayKindsStr) {
  std::vector<PositroniumDecayKind> decayKinds;
  for(auto decayKindStr : decayKindsStr) {
    if (decayKindStr == "k2Gamma") {
      decayKinds.push_back(PositroniumDecayKind::k2Gamma);
    } else if (decayKindStr == "k3Gamma") {
      decayKinds.push_back(PositroniumDecayKind::k3Gamma);
    } else {
      // TODO raise an error?
    }
  }
  return decayKinds;
}

void GatePositroniumSource::GeneratePrimaries(G4Event *event,
                                          double current_simulation_time) {
  auto &ll = GetThreadLocalDataGenericSource();
  ll.fSPS->SetParticleTime(current_simulation_time);
  auto vertex = ll.fSPS->GetPosDist()->VGenerateOne();
  auto number_of_vertices = pModel->GeneratePrimaryVertices(event, current_simulation_time, vertex);
  auto &l = GetThreadLocalData();
  l.fNumberOfGeneratedEvents++;
}
