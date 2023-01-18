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
#include "GateHelpersDict.h"

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

void GateSingleParticleSource::GeneratePrimaryVertex(G4Event *event) {
  // (No mutex needed because variables (position, etc) are local)

  // Generate position & direction until angle is ok
  // bool debug = false;
  bool accept_angle = false;
  bool e_zero = false;
  G4ThreeVector position;
  G4ParticleMomentum momentum_direction;
  fAAManager->StartAcceptLoop();
  while (not accept_angle) {
    // position
    position = fPositionGenerator->VGenerateOne();

    // direction
    momentum_direction = fDirectionGenerator->GenerateOne();

    // accept ?
    accept_angle = fAAManager->TestIfAccept(position, momentum_direction);
    if (not accept_angle and
        fAAManager->GetPolicy() ==
            GateAcceptanceAngleTesterManager::AAZeroEnergy) {
      e_zero = true;
      accept_angle = true;
    }
  }

  // create a new vertex (time must have been set before with SetParticleTime)
  auto *vertex = new G4PrimaryVertex(position, particle_time);

  // energy
  double energy =
      e_zero ? 0 : fEnergyGenerator->VGenerateOne(fParticleDefinition);

  // one single particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(momentum_direction);
  particle->SetCharge(fCharge);

  // FIXME polarization
  // FIXME weight from eneGenerator + bias ? (should not be useful yet ?)

  // set vertex // FIXME change for back to back
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
}

void GateSingleParticleSource::SetAAManager(
    GateAcceptanceAngleTesterManager *aa_manager) {
  fAAManager = aa_manager;
}
