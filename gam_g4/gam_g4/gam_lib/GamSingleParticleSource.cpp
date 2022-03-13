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
#include "GamHelpersDict.h"

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

void GamSingleParticleSource::SetAcceptanceAngleVolumes(std::vector<std::string> v) {
    fAcceptanceAngleVolumeNames = v;
    fAcceptanceAngleFlag = (v.size() != 0);
}

void GamSingleParticleSource::SetAcceptanceAngleParam(py::dict puser_info) {
    //fAcceptanceAngleParam = py::dict(puser_info);
    //DDD(fAcceptanceAngleParam);
    fAcceptanceAngleVolumeNames = DictVecStr(puser_info, "volumes");
    for (auto v: fAcceptanceAngleVolumeNames) {
        DDD(v);
    }
    fAcceptanceAngleFlag = fAcceptanceAngleVolumeNames.size() > 0;

    // FIXME I dont know how to deep copy the input dict !!
    // (it seems to be destroy later, so I cannot use it in InitializeAcceptanceAngle)

    //fAcceptanceAngleParam["intersection_flag"] = puser_info["intersection_flag"];
    //fAcceptanceAngleParam["normal_flag"] = puser_info, "normal_flag");
    //fAcceptanceAngleParam["normal_tolerance"] = DictBool(puser_info, "normal_tolerance");
    //fAcceptanceAngleParam["normal_vector"] = DictBool(puser_info, "normal_vector");
    //DDD(fAcceptanceAngleParam);

    fIntersectionFlag = DictBool(puser_info, "intersection_flag");
    fNormalFlag = DictBool(puser_info, "normal_flag");
    fNormalAngleTolerance = DictFloat(puser_info, "normal_tolerance");
    fNormalVector = Dict3DVector(puser_info, "normal_vector");
}

void GamSingleParticleSource::InitializeAcceptanceAngle() {
    // Create the testers (only the first time)
    if (fAATesters.size() == 0) {
        for (auto name: fAcceptanceAngleVolumeNames) {
            DDD(name);
            auto *t = new GamAcceptanceAngleTester(name,
                                                   fIntersectionFlag, fNormalFlag,
                                                   fNormalAngleTolerance, fNormalVector);
            fAATesters.push_back(t);
        }
    }

    // Update the transform (all runs!)
    for (auto t: fAATesters) t->UpdateTransform();

    // store the ID of this Run
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
    if (fAcceptanceAngleFlag) {
        if (fAALastRunId != G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID())
            InitializeAcceptanceAngle();

        bool shouldSkip = true;
        for (auto tester: fAATesters) {
            bool accept = tester->TestIfAccept(position, momentum_direction);
            if (accept) {
                shouldSkip = false;
                continue;
            }
        }
        if (shouldSkip) {
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
    // FIXME weight from eneGenerator + bias ? (should not be useful yet ?)

    // set vertex // FIXME change for back to back
    vertex->SetPrimary(particle);
    event->AddPrimaryVertex(vertex);
}
