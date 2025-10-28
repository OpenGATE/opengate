/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTemplateSource.h"
#include "G4ParticleTable.hh"
#include "GateHelpersDict.h"
#include <G4UnitsTable.hh>

GateTemplateSource::GateTemplateSource() : GateVSource() {
  fN = 0;
  fFloatValue = 0;
}

GateTemplateSource::~GateTemplateSource() {
  // nothing
}

void GateTemplateSource::InitializeUserInfo(py::dict &user_info) {
  GateVSource::InitializeUserInfo(user_info);
  // get user info about activity or nb of events
  fN = DictGetInt(user_info, "n");
  fFloatValue = DictGetDouble(user_info, "float_value");
  fVectorValue = DictGetVecDouble(user_info, "vector_value");
  // Check parameters
  if (fVectorValue.size() != 3) {
    Fatal("Error, fVectorValue must be size 3");
  }
}

void GateTemplateSource::PrepareNextRun() {
  // The following compute the global transformation from
  // the local volume (mother) to the world
  GateVSource::PrepareNextRun();

  // The global transformation to apply for the current RUN is known in :
  // fGlobalTranslation & fGlobalRotation

  // init the number of generated events (here, for each run)
  fNumberOfGeneratedEvents = 0;
}

void GateTemplateSource::GeneratePrimaries(G4Event *event,
                                           double current_simulation_time) {

  // create a particle type (may be done during the initialization if
  // it is always the same type)
  auto *particle_table = G4ParticleTable::GetParticleTable();
  auto *fParticleDefinition = particle_table->FindParticle("gamma");

  // create the primary particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(fFloatValue);
  particle->SetMomentumDirection(G4ThreeVector(1, 0, 0));

  // the position is changed according to fGlobalTranslation and fGlobalRotation
  auto pos = G4ThreeVector(fVectorValue[0], fVectorValue[1], fVectorValue[2]);
  auto &l = fThreadLocalData.Get();
  pos = l.fGlobalRotation * pos + l.fGlobalTranslation;

  // create the vertex
  auto *vertex = new G4PrimaryVertex(pos, current_simulation_time);
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
  fNumberOfGeneratedEvents++;
}
