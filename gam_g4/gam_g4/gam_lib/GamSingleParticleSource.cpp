/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include "G4PrimaryVertex.hh"
#include "G4Event.hh"
#include "G4RunManager.hh"
#include "GamSingleParticleSource.h"
#include "GamHelpersDict.h"

GamSingleParticleSource::GamSingleParticleSource(std::string /*mother_volume*/) {
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
    fAcceptanceAngleFlag = false;
    fAASkippedParticles = 0;
    fAALastRunId = -1;
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


void GamSingleParticleSource::SetAcceptanceAngleParam(py::dict puser_info) {
    fAcceptanceAngleVolumeNames = DictGetVecStr(puser_info, "volumes");
    fAcceptanceAngleFlag = !fAcceptanceAngleVolumeNames.empty();
    // (we cannot use py::dict here as it is lost at the end of the function)
    fAcceptanceAngleParam = DictToMap(puser_info);
}

void GamSingleParticleSource::InitializeAcceptanceAngle() {
    // Create the testers (only the first time)
    if (fAATesters.empty()) {
        for (const auto &name: fAcceptanceAngleVolumeNames) {
            auto *t = new GamAcceptanceAngleTester(name, fAcceptanceAngleParam);
            fAATesters.push_back(t);
        }
    }

    // Update the transform (all runs!)
    for (auto *t: fAATesters) t->UpdateTransform();

    // store the ID of this Run
    fAALastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
}

bool GamSingleParticleSource::TestIfAcceptAngle(const G4ThreeVector &position,
                                                const G4ThreeVector &momentum_direction) {
    // If angle acceptance flag is enabled, we check if the particle is going to intersect the given volume.
    // If not, the energy is set to zero to ignore
    // We must initialize the angle every run because the associated volume may have moved
    if (!fAcceptanceAngleFlag) return true;

    if (fAALastRunId != G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID())
        InitializeAcceptanceAngle();

    bool shouldSkip = true;
    for (auto *tester: fAATesters) {
        bool accept = tester->TestIfAccept(position, momentum_direction);
        if (accept) {
            shouldSkip = false;
            continue;
        }
    }
    if (shouldSkip) {
        fAASkippedParticles++;
        return false;
    }
    return true;
}

void GamSingleParticleSource::GeneratePrimaryVertex(G4Event *event) {
    // (No mutex needed because variables (position, etc) are local)

    // position
    auto position = fPositionGenerator->VGenerateOne();

    // create a new vertex (time must have been set before with SetParticleTime)
    auto *vertex = new G4PrimaryVertex(position, particle_time);

    // direction
    auto momentum_direction = fDirectionGenerator->GenerateOne();

    // If angle acceptance, we check if the particle is going to intersect the given volume.
    // If not, the energy is set to zero to ignore
    double energy = 0;
    bool accept = TestIfAcceptAngle(position, momentum_direction);
    if (accept) {
        energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);
    }

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
