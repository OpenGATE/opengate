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
    DDD("InitializeAcceptanceAngle");
    DDD(fAngleAcceptanceVolumeName);
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
        //auto world = pvs->GetVolume(fMother);
        fAANavigator = new G4Navigator();
        fAANavigator->SetWorldVolume(world);
    }

    // Get the transform matrix from world to volume coordinate system
    // (assume one single replica)
    fAATransform = fAANavigator->GetMotherToDaughterTransform(fAAPhysicalVolume, 0, kNormal);
    DDD(fAATransform.NetTranslation());
    DDD(fAATransform.NetRotation());


    // FIXME
    G4ThreeVector tr;
    //auto *rot = new G4RotationMatrix;
    fAARotation = new G4RotationMatrix;
    ComputeTransformationFromWorldToVolume(fAngleAcceptanceVolumeName, tr, *fAARotation);
    //ComputeTransformationFromVolumeToWorld(fAngleAcceptanceVolumeName, tr, *rot);
    DDD(tr);
    DDD(*fAARotation);
    //fAARotation->invert();
    fAATransform = G4AffineTransform(fAARotation->inverse(), tr);
    DDD(fAATransform.NetRotation());

    // store the ID of the Run
    fAALastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
    DDD(fAALastRunId);
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
    // We must initialize the angle every run because the associated volume may have moved
    if (fAngleAcceptanceFlag) {
        if (fAALastRunId != G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID()) InitializeAcceptanceAngle();
        //DDD(position);
        auto localPosition = fAATransform.TransformPoint(position);
        //DDD(localPosition);
        //DDD(momentum_direction);
        //auto rot = fAATransform.NetRotation();
        //DDD(rot);
        //rot.invert();
        //rot = *fAARotation;
        //DDD(rot);
        auto localDirection = (*fAARotation) * (momentum_direction);
        //DDD(localDirection);
        //momentum_direction = localDirection;
        auto dist = fAASolid->DistanceToIn(localPosition, localDirection);
        //DDD(dist);
        if (dist == kInfinity) {
            fAASkippedParticles++;
            energy = 0;
            //momentum_direction = G4ThreeVector(0,0,0);
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
