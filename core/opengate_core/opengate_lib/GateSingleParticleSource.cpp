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
#include "biasing/GateForcedDirectionManager.h"

GateSingleParticleSource::GateSingleParticleSource(
    std::string /*mother_volume*/) {
  fPositionGenerator = new GateSPSPosDistribution();
  fDirectionGenerator = new GateSPSAngDistribution();
  fEnergyGenerator = new GateSPSEneDistribution();
  fAAManager = nullptr;
  fFDManager = nullptr;

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
  fAccolinearitySigma = 0.0;
  fPolarizationFlag = false;
}

GateSingleParticleSource::~GateSingleParticleSource() {
  delete fPositionGenerator;
  delete fDirectionGenerator;
  delete fEnergyGenerator;
  delete fAAManager;
  delete fFDManager;
  delete fBiasRndm;
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

void GateSingleParticleSource::SetPolarization(G4ThreeVector &polarization) {
  fPolarization = polarization;
  fPolarizationFlag = true;
}

G4ThreeVector GateSingleParticleSource::GenerateDirectionWithAA(
    const G4ThreeVector &position, bool &zero_energy_flag) const {
  // Rejection method: generate the direction until the angle is acceptable
  bool accept_angle = false;
  zero_energy_flag = false;
  G4ParticleMomentum direction;
  fAAManager->StartAcceptLoop();
  while (!accept_angle) {
    // direction
    direction = fDirectionGenerator->VGenerateOne();

    // accept ?
    accept_angle = fAAManager->TestIfAccept(position, direction);
    if (!accept_angle &&
        fAAManager->GetPolicy() == GateAcceptanceAngleManager::AAZeroEnergy) {
      zero_energy_flag = true;
      accept_angle = true;
    }
  }
  return direction;
}

void GateSingleParticleSource::GeneratePrimaryVertex(G4Event *event) {
  // (No mutex needed because variables (position, etc.) are local)

  // Generate position
  const auto position = fPositionGenerator->VGenerateOne();

  G4ThreeVector direction;
  double weight = 1.0;
  bool zero_energy_flag = false;
  if (fAAManager->IsEnabled()) {
    // Generate the direction (until angle is ok or too many trials)
    direction = GenerateDirectionWithAA(position, zero_energy_flag);
  } else {
    if (fFDManager->IsEnabled()) {
      direction = fFDManager->GenerateForcedDirection(position,
                                                      zero_energy_flag, weight);
    } else {
      direction = fDirectionGenerator->VGenerateOne();
    }
  }

  // energy
  const double energy =
      zero_energy_flag ? 0
                       : fEnergyGenerator->VGenerateOne(fParticleDefinition);

  // back to back photon?
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
  particle->SetWeight(weight);
  if (fPolarizationFlag)
    particle->SetPolarization(fPolarization);

  // FIXME weight from eneGenerator + bias ? (should not be useful yet ?)

  // set vertex
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
}

void GateSingleParticleSource::SetBackToBackMode(const bool flag,
                                                 const bool accolinearityFlag) {
  fBackToBackMode = flag;
  fAccolinearityFlag = accolinearityFlag;
}

void GateSingleParticleSource::SetAccolinearityFWHM(
    const double accolinearityFWHM) {
  fAccolinearitySigma = accolinearityFWHM / CLHEP::rad * fwhm_to_sigma;
}

void GateSingleParticleSource::GeneratePrimaryVertexBackToBack(
    G4Event *event, const G4ThreeVector &position,
    const G4ThreeVector &direction, const double energy) const {
  // create the primary vertex with 2 associated primary particles
  auto *vertex = new G4PrimaryVertex(position, particle_time);

  auto *particle1 = new G4PrimaryParticle(fParticleDefinition);
  particle1->SetKineticEnergy(energy);
  particle1->SetMomentumDirection(direction);

  auto *particle2 = new G4PrimaryParticle(fParticleDefinition);
  particle2->SetKineticEnergy(energy);
  if (fAccolinearityFlag) {
    const double phi = G4RandGauss::shoot(0.0, fAccolinearitySigma);
    const double psi = G4RandGauss::shoot(0.0, fAccolinearitySigma);
    const double theta = sqrt(pow(phi, 2.0) + pow(psi, 2.0));
    G4ThreeVector particle2_direction(sin(theta) * phi / theta,
                                      sin(theta) * psi / theta, cos(theta));
    // TODO: What to do with the magnitude of momentum?
    // Apply accolinearity deviation relative to the collinear case
    particle2_direction.rotateUz(-1.0 * particle1->GetMomentum().unit());
    particle2->SetMomentumDirection(particle2_direction);
  } else {
    particle2->SetMomentumDirection(-direction);
  }

  // Associate the two primaries with the vertex
  vertex->SetPrimary(particle1);
  vertex->SetPrimary(particle2);
  event->AddPrimaryVertex(vertex);
}

void GateSingleParticleSource::SetAAManager(
    GateAcceptanceAngleManager *aa_manager) {
  fAAManager = aa_manager;
}

void GateSingleParticleSource::SetFDManager(
    GateForcedDirectionManager *fd_manager) {
  fFDManager = fd_manager;
}
