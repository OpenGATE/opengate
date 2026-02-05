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
  fA = 0;
  fZ = 0;
  fE = 0;
  fWeight = -1;
  fWeightSigma = -1;
  fInitialActivity = 0;
  fParticleDefinition = nullptr;
  //fDirectionRelativeToAttachedVolume = false;
  //fUserParticleLifeTime = -1;
  //fBackToBackMode = false;

  
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

//void GatePositroniumSource::SetEnergyCDF(const std::vector<double> &cdf) {
  //fEnergyCDF = cdf;
//}

//void GatePositroniumSource::SetProbabilityCDF(const std::vector<double> &cdf) {
  //fProbabilityCDF = cdf;
//}

//void GatePositroniumSource::SetTAC(const std::vector<double> &times,
                               //const std::vector<double> &activities) {
  //fTAC_Times = times;
  //fTAC_Activities = activities;
//}

void GatePositroniumSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  CreateSPS();

  auto prompt_photon_energies = DictGetVecDouble(user_info,"prompt_photon_energies");
  auto prompt_photon_probabilities = DictGetVecDouble(user_info,"prompt_photon_probabilities");
  auto decay_kinds = DictGetVecStr(user_info,"decay_kinds");
  auto lifetimes = DictGetVecDouble(user_info,"positronium_lifetimes");
  auto fractions = DictGetVecDouble(user_info, "positronium_fractions");
  auto bla =  DictGetDouble(user_info, "bla");
  std::cout << "bla:"<<bla << std::endl;
  std::cout << "fractions :"<<fractions[0]  << std::endl;
  PositroniumDecayModelParams params;
  params.fFractions={0.4, 0.6};
  params.fLifetimes={0.1244f, 2.f};
  params.fDecayKind={PositroniumDecayKind::k2Gamma, PositroniumDecayKind::k2Gamma};
  params.fPromptGammaProbabilities = {0.0f, 0.0f};
  params.fPromptGammaEnergy = {0.0f, 0.0f};

  pModel = std::make_unique<GatePositroniumDecayModel>(params);

  // weight
  fWeight = DictGetDouble(user_info, "weight");
  fWeightSigma = DictGetDouble(user_info, "weight_sigma");
  //fUserParticleLifeTime = DictGetDouble(user_info, "user_particle_life_time");

  // get the user info for the particle
  //InitializeParticle(user_info);

  // position, direction, energy
  //InitializePosition(user_info);
  //InitializeDirection(user_info);
  //InitializeEnergy(user_info);

  // FIXME todo polarization

  // init number of events
  //fDirectionRelativeToAttachedVolume =
      //DictGetBool(user_info, "direction_relative_to_attached_volume");
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
  //if (ll.fInitGenericIon) {
    //auto *ion_table = G4IonTable::GetIonTable();
    //auto *ion = ion_table->GetIon(fZ, fA, fE);
    //ll.fSPS->SetParticleDefinition(ion);
    //SetLifeTime(ion);
    ////auto *ion_table = G4IonTable::GetIonTable();
    ////auto *ion = ion_table->GetIon(fZ, fA, fE);
    ////ll.fSPS->SetParticleDefinition(ion);
    ////SetLifeTime(ion);
    //ll.fInitGenericIon = false; // only the first time
  //}
  //
  //G4ThreeVector particle_position = GetPosDist()->GenerateOne();
  //ChangeParticlePositionRelativeToAttachedVolume(particle_position);
  ll.fSPS->SetParticleTime(current_simulation_time);
  //ll.fSPS->GeneratePrimaryVertex(event);
  auto vertex = ll.fSPS->GetPosDist()->VGenerateOne();
  //std::cout << "vertex:"<< vertex.x()<<","<< vertex.y()<< ","<< vertex.z()<< std::endl;
  //std::cout << "time:"<< current_simulation_time<< std::endl;
  auto number_of_vertices = pModel->GeneratePrimaryVertices(event, current_simulation_time, vertex);
  //std::cout << "number_of_vertices :"<< number_of_vertices << std::endl;

  auto &l = GetThreadLocalData();
  l.fNumberOfGeneratedEvents++;
}

//void GatePositroniumSource::GeneratePrimaries(G4Event *event,
                                          //double current_simulation_time) {
  //auto &ll = GetThreadLocalDataGenericSource();
  //// Generic ion cannot be created at initialization.
  //// It must be created the first time we get there
  //if (ll.fInitGenericIon) {
    //auto *ion_table = G4IonTable::GetIonTable();
    //auto *ion = ion_table->GetIon(fZ, fA, fE);
    //ll.fSPS->SetParticleDefinition(ion);
    //SetLifeTime(ion);
    //ll.fInitGenericIon = false; // only the first time
  //}

  //// Confine cannot be initialized at initialization (because need all volumes
  //// to be created) It must be set here, the first time we get there
  //if (ll.fInitConfine) {
    //auto *pos = ll.fSPS->GetPosDist();
    //pos->ConfineSourceToVolume(fConfineVolume);
    //ll.fInitConfine = false;
  //}

  //// sample the particle properties with SingleParticleSource
  //// (acceptance angle is included)
  //ll.fSPS->SetParticleTime(current_simulation_time);
  //ll.fSPS->GeneratePrimaryVertex(event);

  //// update the time according to skipped events
  //ll.fEffectiveEventTime = current_simulation_time;
  //if (ll.fAAManager->IsEnabled()) {
    //if (ll.fAAManager->GetPolicy() ==
        //GateAcceptanceAngleTesterManager::AASkipEvent) {
      //UpdateEffectiveEventTime(current_simulation_time,
                               //ll.fAAManager->GetNumberOfNotAcceptedEvents());
      //ll.fCurrentSkippedEvents = ll.fAAManager->GetNumberOfNotAcceptedEvents();
      //event->GetPrimaryVertex(0)->SetT0(ll.fEffectiveEventTime);
    //} else {
      //ll.fCurrentZeroEvents =
          //ll.fAAManager->GetNumberOfNotAcceptedEvents(); // 1 or 0
    //}
  //}

  //// weight ?
  //if (fWeight > 0) {
    //if (fWeightSigma < 0) {
      //for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
        //event->GetPrimaryVertex(i)->SetWeight(fWeight);
      //}
    //} else { // weight is Gaussian
      //for (auto i = 0; i < event->GetNumberOfPrimaryVertex(); i++) {
        //double w = G4RandGauss::shoot(fWeight, fWeightSigma);
        //event->GetPrimaryVertex(i)->SetWeight(w);
      //}
    //}
  //}

  //auto &l = GetThreadLocalData();
  //l.fNumberOfGeneratedEvents++;
//}

void GatePositroniumSource::InitializeParticle(py::dict &user_info) {
  auto &ll = fThreadLocalDataGenericSource.Get();
  std::string pname = DictGetStr(user_info, "particle");
  // Is the particle an ion (name start with ion) ?
  if (pname.rfind("ion", 0) == 0) {
    //InitializeIon(user_info);
    return;
  }
  ll.fInitGenericIon = false;
}

//void GatePositroniumSource::InitializeIon(py::dict &user_info) {
  //auto u = py::dict(user_info["ion"]);
  //fA = DictGetInt(u, "A");
  //fZ = DictGetInt(u, "Z");
  //fE = DictGetDouble(u, "E");
  //auto &ll = fThreadLocalDataGenericSource.Get();
  //ll.fInitGenericIon = true;
//}




//void GatePositroniumSource::SetLifeTime(G4ParticleDefinition *p) {
  //// Do nothing it the given life-time is negative (default)
  //if (fUserParticleLifeTime < 0)
    //return;
  //// We set the LifeTime as proposed by the user
  //p->SetPDGLifeTime(fUserParticleLifeTime);
//}

