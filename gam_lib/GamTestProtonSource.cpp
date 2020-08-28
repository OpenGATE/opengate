/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamTestProtonSource.h"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4RandomTools.hh"

GamTestProtonSource::GamTestProtonSource() : G4VUserPrimaryGeneratorAction() {
    fParticleGun = new G4ParticleGun(1);
    auto particleTable = G4ParticleTable::GetParticleTable();
    auto particle = particleTable->FindParticle("proton");
    fParticleGun->SetParticleDefinition(particle);
    fParticleGun->SetParticleEnergy(150 * MeV);
    fParticleGun->SetParticleMomentumDirection(G4ThreeVector(0, 0, 1));
}

void GamTestProtonSource::GeneratePrimaries(G4Event *anEvent) {
    // std::cout << "GeneratePrimaries event " << std::endl;
    auto diameter = 20.0 * mm;
    auto x0 = diameter * (G4UniformRand() - 0.5);
    auto y0 = diameter * (G4UniformRand() - 0.5);
    auto z0 = 0.0;
    // std::cout << "xyz " << x0 << " " << y0 << " " << z0 << std::endl;
    fParticleGun->SetParticlePosition(G4ThreeVector(x0, y0, z0));
    fParticleGun->GeneratePrimaryVertex(anEvent);
}