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

GatePositroniumSource::GatePositroniumSource() : GateVSource() {
}

GatePositroniumSource::~GatePositroniumSource() {
  // FIXME: we cannot really delete fSPS and fAAManager
  // I dont know exactly why.
  // Maybe because it has been created in a thread which
  // can be different from the thread that delete.
  auto &l = fThreadLocalDataGenericSource.Get();
  if (l.fAAManager != nullptr) {
    // delete l.fAAManager;
  }
  // delete fSPS;
}

GatePositroniumSource::threadLocalGenericSource &
GatePositroniumSource::GetThreadLocalDataGenericSource() {
  return fThreadLocalDataGenericSource.Get();
}


void GatePositroniumSource::CreateSPS() {
  auto &l = fThreadLocalDataGenericSource.Get();
  l.fSPS = new GateSingleParticleSource(fAttachedToVolumeName);
}

void GatePositroniumSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  CreateSPS();

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

  // position
  //InitializePosition(user_info);
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

double GatePositroniumSource::PrepareNextTime(double current_simulation_time) {
  auto &ll = GetThreadLocalDataGenericSource();
  // initialization of the effective event time (it can be in the
  // future according to the current_simulation_time)
  if (ll.fEffectiveEventTime < current_simulation_time) {
    ll.fEffectiveEventTime = current_simulation_time;
  }
  UpdateActivity(ll.fEffectiveEventTime);
  //fTotalSkippedEvents += ll.fCurrentSkippedEvents; // FIXME lock ?
  //fTotalZeroEvents += ll.fCurrentZeroEvents;
  ll.fCurrentZeroEvents = 0;
  auto cse = ll.fCurrentSkippedEvents;
  ll.fCurrentSkippedEvents = 0;

  // if MaxN is below zero, we check the time
  if (fMaxN <= 0) {
    if (ll.fEffectiveEventTime < fStartTime)
      return fStartTime;
    if (ll.fEffectiveEventTime >= fEndTime)
      return -1;

    // get next time according to current fActivity
    double next_time = CalcNextTime(ll.fEffectiveEventTime);
    if (next_time >= fEndTime)
      return -1;
    return next_time;
  }

  // check according to t MaxN
  auto &l = GetThreadLocalData();
  if (l.fNumberOfGeneratedEvents + cse >= fMaxN) {
    return -1;
  }
  return fStartTime;
}

void GatePositroniumSource::PrepareNextRun() {
  // The following function computes the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();

  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto &l = GetThreadLocalData();
  auto &ll = GetThreadLocalDataGenericSource();
  auto *pos = ll.fSPS->GetPosDist();
  pos->SetCentreCoords(l.fGlobalTranslation);

  // orientation according to mother volume
  auto rotation = l.fGlobalRotation;
  G4ThreeVector r1(rotation(0, 0), rotation(1, 0), rotation(2, 0));
  G4ThreeVector r2(rotation(0, 1), rotation(1, 1), rotation(2, 1));
  pos->SetPosRot1(r1);
  pos->SetPosRot2(r2);

  // For the direction, the orientation may or may not be
  // relative to the volume according to user option

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
