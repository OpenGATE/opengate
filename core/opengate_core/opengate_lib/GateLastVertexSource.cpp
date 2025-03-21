/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateLastVertexSource.h"
#include "G4ParticleTable.hh"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GateLastVertexSource::GateLastVertexSource() : GateVSource() {}

GateLastVertexSource::~GateLastVertexSource() {}

void GateLastVertexSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  // get user info about activity or nb of events
  fN = DictGetInt(user_info, "n");
  fActivity = DictGetDouble(user_info, "activity");

  if (fActivity != 0) {
    fN = int(fActivity / CLHEP::Bq);
  }
}

double GateLastVertexSource::PrepareNextTime(double current_simulation_time) {

  /*
  // If all N events have been generated, we stop (negative time)
  if (fNumberOfGeneratedEvents >= fN){
    std::cout << "LV: "<< -1<<"  "<< fNumberOfGeneratedEvents <<"  "<<
  fN<<std::endl; return -1;
  }

   if (fListOfContainer.size()==0){
    std::cout << "LV: "<< 1<<"  "<<fNumberOfGeneratedEvents <<"  "<<
  fN<<std::endl; return 1;
  }
  // Else we consider all event with a timestamp equal to the simulation
  // StartTime
  std::cout << "LV: "<< fStartTime<<"  "<<fNumberOfGeneratedEvents <<"  "<<
  fN<<std::endl; return fStartTime;
  */

  // if (fNumberOfGeneratedEvents >= fN)
  return -1;

  // return fStartTime + 1;
}

void GateLastVertexSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();

  // The global transformation to apply for the current RUN is known in :
  // fGlobalTranslation & fGlobalRotation

  // init the number of generated events (here, for each run)
  fNumberOfGeneratedEvents = 0;
}

void GateLastVertexSource::GenerateOnePrimary(G4Event *event,
                                              double current_simulation_time,
                                              G4int idx) {

  if (fNumberOfGeneratedEvents >= fN) {
    auto *particle_table = G4ParticleTable::GetParticleTable();
    auto *fParticleDefinition = particle_table->FindParticle("geantino");
    auto *particle = new G4PrimaryParticle(fParticleDefinition);
    particle->SetKineticEnergy(0);
    particle->SetMomentumDirection({1, 0, 0});
    particle->SetWeight(1);
    auto *vertex = new G4PrimaryVertex({0, 0, 0}, current_simulation_time);
    vertex->SetPrimary(particle);
    event->AddPrimaryVertex(vertex);
  } else {

    SimpleContainer containerToSplit =
        fListOfContainer[idx].GetContainerToSplit();
    G4double energy = containerToSplit.GetEnergy();
    if (energy < 0) {
      energy = 0;
    }
    fContainer = fListOfContainer[idx];
    G4ThreeVector position = containerToSplit.GetVertexPosition();
    G4ThreeVector momentum = containerToSplit.GetMomentum();
    G4String particleName = containerToSplit.GetParticleNameToSplit();
    G4double weight = containerToSplit.GetWeight();
    fProcessToSplit = containerToSplit.GetProcessNameToSplit();
    auto &l = fThreadLocalData.Get();
    auto *particle_table = G4ParticleTable::GetParticleTable();
    auto *fParticleDefinition = particle_table->FindParticle(particleName);
    auto *particle = new G4PrimaryParticle(fParticleDefinition);
    particle->SetKineticEnergy(energy);
    particle->SetMomentumDirection(momentum);
    particle->SetWeight(weight);
    auto *vertex = new G4PrimaryVertex(position, current_simulation_time);
    vertex->SetPrimary(particle);
    event->AddPrimaryVertex(vertex);
  }
}

void GateLastVertexSource::GeneratePrimaries(G4Event *event,
                                             double current_simulation_time) {

  GenerateOnePrimary(event, current_simulation_time, fNumberOfGeneratedEvents);
  fNumberOfGeneratedEvents++;
  if (fNumberOfGeneratedEvents == fListOfContainer.size()) {
    fListOfContainer.clear();
  }
}
