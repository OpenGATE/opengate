/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include "GamSingleParticleSource.h"
#include "G4PrimaryVertex.hh"
#include "G4Event.hh"

GamSingleParticleSource::GamSingleParticleSource() {
    fPositionGenerator = new GamSPSPosDistribution();
    fDirectionGenerator = new G4SPSAngDistribution();
    fEnergyGenerator = new GamSPSEneDistribution();

    // needed
    fBiasRndm = new G4SPSRandomGenerator();
    fPositionGenerator->SetBiasRndm(fBiasRndm);
    fDirectionGenerator->SetBiasRndm(fBiasRndm);
    fDirectionGenerator->SetPosDistribution(fPositionGenerator);
    fEnergyGenerator->SetBiasRndm(fBiasRndm);
}

GamSingleParticleSource::~GamSingleParticleSource() {
    delete fPositionGenerator;
    delete fDirectionGenerator;
    delete fEnergyGenerator;
}

void GamSingleParticleSource::SetPosGenerator(GamSPSPosDistribution *pg) {
    fPositionGenerator = pg;
    fPositionGenerator->SetBiasRndm(fBiasRndm);
    fDirectionGenerator->SetPosDistribution(fPositionGenerator);
}


void GamSingleParticleSource::SetParticleDefinition(G4ParticleDefinition *def) {
    fParticleDefinition = def;
    fCharge = fParticleDefinition->GetPDGCharge();
    fMass = fParticleDefinition->GetPDGMass();
}

void GamSingleParticleSource::GeneratePrimaryVertex(G4Event *event) {
    // FIXME Mutex needed ? No because variables (position, etc) are local.

    // position
    auto position = fPositionGenerator->VGenerateOne();

    // create a new vertex (time must have been set before with SetParticleTime)
    G4PrimaryVertex *vertex = new G4PrimaryVertex(position, particle_time);

    // direction
    auto momentum_direction = fDirectionGenerator->GenerateOne();

    // energy
    auto energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);

    // one single particle
    auto particle = new G4PrimaryParticle(fParticleDefinition);
    particle->SetKineticEnergy(energy);
    particle->SetMass(fMass);
    particle->SetMomentumDirection(momentum_direction);
    particle->SetCharge(fCharge);

    // FIXME polarization
    // FIXME weight from eneGenerator + bias ? (should not be useful yet)

    // set vertex // FIXME change for back to back
    vertex->SetPrimary(particle);
    event->AddPrimaryVertex(vertex);
}
