/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include "G4PrimaryVertex.hh"
#include "G4Event.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4RandomTools.hh"
#include "GamSingleParticleSource.h"

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

    // Acceptance angle
    fAngleAcceptanceFlag = false;
    fAASolid = nullptr;
    fSkippedParticles = 0;
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

void GamSingleParticleSource::SetAngleAcceptanceVolume(std::string v) {
    fAngleAcceptanceVolume = v;
    fAngleAcceptanceFlag = true;
}

void GamSingleParticleSource::InitializeAcceptanceAngle() {
    // Retrieve the solid (from the logical volume)
    auto lvs = G4LogicalVolumeStore::GetInstance();
    auto lv = lvs->GetVolume(fAngleAcceptanceVolume);
    fAASolid = lv->GetSolid();

    // Retrieve the physical volume
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto pv = pvs->GetVolume(fAngleAcceptanceVolume);

    // Init a navigator that will be used to find the transform
    auto world = pvs->GetVolume("world");
    auto fNavigator = new G4Navigator();
    fNavigator->SetWorldVolume(world);

    // Get the transform matrix from world to volume coordinate system
    // (assume one single replica)
    fAATransform = fNavigator->GetMotherToDaughterTransform(pv, 0, kNormal);
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

    // If angle acceptance, we check if the particle is going to intersect the given volume.
    // If not, the energy is set to zero to ignore
    if (fAngleAcceptanceFlag) {
        if (fAASolid == nullptr) InitializeAcceptanceAngle(); // FIXME run ?
        auto localPosition = fAATransform.TransformPoint(position);
        auto dist = fAASolid->DistanceToIn(localPosition, momentum_direction);
        if (dist == kInfinity) {
            fSkippedParticles++;
            energy = 0;
        }
    }

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
