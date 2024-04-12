/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSingleParticleSource.h"
#include "G4Event.hh"
#include "G4PrimaryVertex.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"

#include "GateRandomMultiGauss.h"

GateSingleParticleSource::GateSingleParticleSource(
    std::string /*mother_volume*/) {
  fPositionGenerator = new GateSPSPosDistribution();
  fDirectionGenerator = new G4SPSAngDistribution();
  fEnergyGenerator = new GateSPSEneDistribution();

  // needed
  fBiasRndm = new G4SPSRandomGenerator();
  fPositionGenerator->SetBiasRndm(fBiasRndm);
  fDirectionGenerator->SetBiasRndm(fBiasRndm);
  fDirectionGenerator->SetPosDistribution(fPositionGenerator);
  fEnergyGenerator->SetBiasRndm(fBiasRndm);

  // init
  fMass = 0;
  fCharge = 0;
  fParticleDefinition = nullptr;
  fBackToBackMode = false;
  fAccolinearityFlag = false;
}

GateSingleParticleSource::~GateSingleParticleSource() {
  delete fPositionGenerator;
  delete fDirectionGenerator;
  delete fEnergyGenerator;
}

void GateSingleParticleSource::SetPosGenerator(GateSPSPosDistribution *pg) {
  fPositionGenerator = pg;
  fPositionGenerator->SetBiasRndm(fBiasRndm);
  fDirectionGenerator->SetPosDistribution(fPositionGenerator);
}

void GateSingleParticleSource::SetParticleDefinition(
    G4ParticleDefinition *def) {
  fParticleDefinition = def;
  fCharge = fParticleDefinition->GetPDGCharge();
  fMass = fParticleDefinition->GetPDGMass();
}

G4ThreeVector
GateSingleParticleSource::GenerateDirectionWithAA(const G4ThreeVector &position,
                                                  bool &zero_energy_flag) {
  // Rejection method : generate direction until angle is ok
  // bool debug = false;
  bool accept_angle = false;
  zero_energy_flag = false;
  G4ParticleMomentum direction;
  fAAManager->StartAcceptLoop();
  while (!accept_angle) {
    // direction
    direction = fDirectionGenerator->GenerateOne();
    // accept ?
    accept_angle = fAAManager->TestIfAccept(position, direction);
    if (!accept_angle && fAAManager->GetPolicy() ==
                             GateAcceptanceAngleTesterManager::AAZeroEnergy) {
      zero_energy_flag = true;
      accept_angle = true;
    }
  }
  return direction;
}

void GateSingleParticleSource::GeneratePrimaryVertex(G4Event *event) {
  // (No mutex needed because variables (position, etc.) are local)

  // Generate position
  auto position = fPositionGenerator->VGenerateOne();

  // Generate direction (until angle is ok)
  bool zero_energy_flag;
  auto direction = GenerateDirectionWithAA(position, zero_energy_flag);

  // energy
  double energy = zero_energy_flag
                      ? 0
                      : fEnergyGenerator->VGenerateOne(fParticleDefinition);

  // back to back photon ?
  if (fBackToBackMode)
    return GeneratePrimaryVertexBackToBack(event, position, direction, energy);

  // create a new vertex (time must have been set before with SetParticleTime)
  auto *vertex = new G4PrimaryVertex(position, particle_time);

  // one single particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(direction);
  particle->SetCharge(fCharge);

  // FIXME polarization
  // FIXME weight from eneGenerator + bias ? (should not be useful yet ?)

  // set vertex
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
}

void GateSingleParticleSource::SetBackToBackMode(bool flag,
                                                 bool accolinearityFlag) {
  fBackToBackMode = flag;
  fAccolinearityFlag = accolinearityFlag;
}

void GateSingleParticleSource::GeneratePrimaryVertexBackToBack(
    G4Event *event, G4ThreeVector &position, G4ThreeVector &direction,
    double energy) {
  // create the primary vertex with 2 associated primary particles
  auto *vertex = new G4PrimaryVertex(position, particle_time);

  auto *particle1 = new G4PrimaryParticle(fParticleDefinition);
  particle1->SetKineticEnergy(energy);
  particle1->SetMomentumDirection(direction);
  auto *particle2 = new G4PrimaryParticle(fParticleDefinition);
  particle2->SetKineticEnergy(energy);
  particle2->SetMomentumDirection(-direction);

  // FIXME: if accolineary flag is true: do something clever
  if (fAccolinearityFlag) {
    Fatal("Accolinearity not implemented yet");
  }

  // Associate the two primaries to the vertex
  vertex->SetPrimary(particle1);
  vertex->SetPrimary(particle2);
  event->AddPrimaryVertex(vertex);
}

void GateSingleParticleSource::SetAAManager(
    GateAcceptanceAngleTesterManager *aa_manager) {
  fAAManager = aa_manager;
}
