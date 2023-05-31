/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePhaseSpaceSource.h"
#include "G4ParticleTable.hh"
#include "G4UnitsTable.hh"
#include "GateHelpersDict.h"

GatePhaseSpaceSource::GatePhaseSpaceSource() : GateVSource() {
  fCurrentIndex = INT_MAX;
  fCharge = 0;
  fMass = 0;
  fCurrentBatchSize = 0;
  fMaxN = 0;
  fGlobalFag = false;
}

GatePhaseSpaceSource::~GatePhaseSpaceSource() = default;

void GatePhaseSpaceSource::InitializeUserInfo(py::dict &user_info) {
  // the following initialize all GenericSource options
  // and the SPS GateSingleParticleSource
  GateVSource::InitializeUserInfo(user_info);

  // Number of events to generate
  fMaxN = DictGetInt(user_info, "n");

  // Batch size
  fCurrentBatchSize = DictGetInt(user_info, "batch_size");
  DDD(fCurrentBatchSize);

  fGlobalFag = DictGetBool(user_info, "global_flag");

  // This is done in GateSingleParticleSource, but we need charge/mass later
  auto pname = DictGetStr(user_info, "particle");
  auto *particle_table = G4ParticleTable::GetParticleTable();
  fParticleDefinition = particle_table->FindParticle(pname);
  fCharge = fParticleDefinition->GetPDGCharge();
  fMass = fParticleDefinition->GetPDGMass();
  DDD(fParticleDefinition->GetParticleName());

  // Init
  fNumberOfGeneratedEvents = 0;
  fCurrentIndex = -1;
}

void GatePhaseSpaceSource::PrepareNextRun() {
  // needed to update orientation wrt mother volume
  // (no need to update th fSPS pos in GateGenericSource)
  // GateVSource::PrepareNextRun();
  // FIXME remove this function ?
  DDD("PrepareNextRun ? move to mother ?");
  GateVSource::PrepareNextRun();
}

double GatePhaseSpaceSource::PrepareNextTime(double current_simulation_time) {
  // check according to t MaxN
  if (fNumberOfGeneratedEvents >= fMaxN) {
    return -1;
  }
  return fStartTime; // FIXME timing ?
}

void GatePhaseSpaceSource::SetGeneratorFunction(ParticleGeneratorType &f) {
  fGenerator = f;
}

void GatePhaseSpaceSource::GenerateBatchOfParticles() {
  // I don't know if we should acquire the GIL or not
  // (does not seem needed)
  // py::gil_scoped_acquire acquire;

  // This function (fGenerator) is defined on Python side
  // It fills all values needed for the particles (position, dir, energy, etc)
  // Alternative: build vector of G4ThreeVector in GenerateBatchOfParticles ?
  // (unsure if it is faster)
  DDD("GenerateBatchOfParticles");
  fGenerator(this);
  fCurrentIndex = 0;
  fCurrentBatchSize = fPositionX.size();
  DDD(fCurrentIndex);
  DDD(fCurrentBatchSize);
}

void GatePhaseSpaceSource::GeneratePrimaries(G4Event *event,
                                             double current_simulation_time) {

  DDD("GeneratePrimaries");
  DDD(current_simulation_time / CLHEP::second)
  DDD(fCurrentIndex);
  DDD(fCurrentBatchSize);
  // If batch is empty, we generate some particles
  if (fCurrentIndex >= fCurrentBatchSize)
    GenerateBatchOfParticles();

  // Go
  GenerateOnePrimary(event, current_simulation_time);

  // update the index;
  fCurrentIndex++;

  // update the number of generated event
  fNumberOfGeneratedEvents++;
}

void GatePhaseSpaceSource::GenerateOnePrimary(G4Event *event,
                                              double current_simulation_time) {
  auto position =
      G4ThreeVector(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
                    fPositionZ[fCurrentIndex]);
  auto direction =
      G4ParticleMomentum(fDirectionX[fCurrentIndex], fDirectionY[fCurrentIndex],
                         fDirectionZ[fCurrentIndex]);
  auto energy = fEnergy[fCurrentIndex];
  auto weight = fWeight[fCurrentIndex];
  // FIXME auto time = fTime[fCurrentIndex];

  // transform according to mother // FIXME
  DDD(fGlobalFag);
  if (not fGlobalFag) {
    DDD(fGlobalTranslation);
    position = fGlobalRotation * position + fGlobalTranslation;
    direction = direction / direction.mag();
    direction = fGlobalRotation * direction;
  }

  // Create the final vertex
  AddOnePrimaryVertex(event, position, direction, energy,
                      current_simulation_time, weight);
}

void GatePhaseSpaceSource::AddOnePrimaryVertex(G4Event *event,
                                               const G4ThreeVector &position,
                                               const G4ThreeVector &direction,
                                               double energy, double time,
                                               double w) const {
  // create primary particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(direction);
  particle->SetCharge(fCharge);

  // set vertex
  auto *vertex = new G4PrimaryVertex(position, time);
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);

  // weights
  event->GetPrimaryVertex(0)->SetWeight(w);
  DDD("End AddOnePrimaryVertex");
}
