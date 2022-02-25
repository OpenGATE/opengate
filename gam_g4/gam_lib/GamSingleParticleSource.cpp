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
#include "G4RunManager.hh"
#include "G4Run.hh"
#include "GamSingleParticleSource.h"
#include "GamHelpersImage.h"

GamSingleParticleSource::GamSingleParticleSource(std::string mother_volume) {
    fMother = mother_volume;
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
    fAASkippedParticles = 0;
    fAALastRunId = -1;
    fAANavigator = nullptr;
    fAAPhysicalVolume = nullptr;
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
    fAngleAcceptanceVolumeName = v;
    fAngleAcceptanceFlag = true;
}

void GamSingleParticleSource::InitializeAcceptanceAngle() {
    // Initialize (only once)
    if (fAANavigator == nullptr) {
        auto lvs = G4LogicalVolumeStore::GetInstance();
        auto lv = lvs->GetVolume(fAngleAcceptanceVolumeName);
        fAASolid = lv->GetSolid();
        // Retrieve the physical volume
        auto pvs = G4PhysicalVolumeStore::GetInstance();
        fAAPhysicalVolume = pvs->GetVolume(fAngleAcceptanceVolumeName);
        // Init a navigator that will be used to find the transform
        auto world = pvs->GetVolume("world");
        fAANavigator = new G4Navigator();
        fAANavigator->SetWorldVolume(world);
    }

    // Get the transformation
    G4ThreeVector tr;
    fAARotation = new G4RotationMatrix;
    ComputeTransformationFromWorldToVolume(fAngleAcceptanceVolumeName, tr, *fAARotation);
    // It is not fully clear why the AffineTransform need the inverse
    fAATransform = G4AffineTransform(fAARotation->inverse(), tr);

    // store the ID of the Run
    fAALastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
}

void GamSingleParticleSource::GeneratePrimaryVertex(G4Event *event) {
    // (No mutex needed because variables (position, etc) are local)

    // position
    auto position = fPositionGenerator->VGenerateOne();

    // create a new vertex (time must have been set before with SetParticleTime)
    G4PrimaryVertex *vertex = new G4PrimaryVertex(position, particle_time);

    // direction
    auto momentum_direction = fDirectionGenerator->GenerateOne();

    double energy = 0;
    // If angle acceptance, we check if the particle is going to intersect the given volume.
    // If not, the energy is set to zero to ignore
    // We must initialize the angle every run because the associated volume may have moved
    if (fAngleAcceptanceFlag) {
        if (fAALastRunId != G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID()) InitializeAcceptanceAngle();
        auto localPosition = fAATransform.TransformPoint(position);
        auto localDirection = (*fAARotation) * (momentum_direction);
        auto dist = fAASolid->DistanceToIn(localPosition, localDirection);
        if (dist == kInfinity) {
            fAASkippedParticles++;
        } else {
            energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);
        }
    } else {
        energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);
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
