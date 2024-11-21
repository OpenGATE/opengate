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
  fDirectionGenerator = new GateSPSAngDistribution();
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
  // Probably an underestimation in most cases, but it is the most cited (Moses
  // 2011)
  // zxc pi must be defined somewhere...
  fAccolinearitySigma = 0.5 / 180.0 * 3.14159265358979323846 * fwhm_to_sigma;
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
    direction = fDirectionGenerator->VGenerateOne();

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

void GateSingleParticleSource::SetAccolinearityFWHM(double accolinearityFWHM) {
  // zxc units agnostic approach?
  fAccolinearitySigma =
      accolinearityFWHM / 180.0 * 3.14159265358979323846 * fwhm_to_sigma;
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
  if (fAccolinearityFlag) {
    double phi = G4RandGauss::shoot(0.0, fAccolinearitySigma);
    double psi = G4RandGauss::shoot(0.0, fAccolinearitySigma);
    double theta = sqrt(pow(phi, 2.0) + pow(psi, 2.0));
    G4ThreeVector particle2_direction(sin(theta) * phi / theta,
                                      sin(theta) * psi / theta, cos(theta));
    // zxc need to keep magnitude of momemtum?
    // Apply accolinearity deviation relative to the colinear case
    particle2_direction.rotateUz(-1.0 * particle1->GetMomentum().unit());
    particle2->SetMomentumDirection(particle2_direction);
  } else {
    particle2->SetMomentumDirection(-direction);
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
