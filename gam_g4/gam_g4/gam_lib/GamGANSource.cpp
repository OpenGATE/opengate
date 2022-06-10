/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GamGANSource.h"
#include "GamHelpersDict.h"

GamGANSource::GamGANSource() : GamGenericSource() {
    fCurrentIndex = 0;
    // for debug, we count the number of E<=0
    fNumberOfSkippedParticles = 0;
    fCharge = 0;
    fMass = 0;
    fUseWeight = false;
    fUseTime = false;
    fUseTimeRelative = false;
    fEnergyThreshold = -1;
}

GamGANSource::~GamGANSource() {
}

void GamGANSource::InitializeUserInfo(py::dict &user_info) {
    GamGenericSource::InitializeUserInfo(user_info);
    fEnergyThreshold = DictGetDouble(user_info, "energy_threshold");

    fCharge = fParticleDefinition->GetPDGCharge();
    fMass = fParticleDefinition->GetPDGMass();
}

void GamGANSource::PrepareNextRun() {
    // needed to update orientation wrt mother volume
    GamVSource::PrepareNextRun();
}

void GamGANSource::SetGeneratorFunction(ParticleGeneratorType &f) {
    fGenerator = f;
}

void GamGANSource::GetParticlesInformation() {
    // I don't know if we should acquire the GIL or not
    // (does not seem needed)
    // py::gil_scoped_acquire acquire;

    // This function (fGenerator) is defined on Python side
    // It fills all values needed for the particles (position, direction, energy, weight)
    fGenerator(this);
    fCurrentIndex = 0;
    // alternative: build vector of G4ThreeVector in GetParticlesInformation
    // (unsure if faster)
}

void GamGANSource::GeneratePrimaries(G4Event *event, double current_simulation_time) {
    if (fCurrentIndex >= fPositionX.size()) {
        GetParticlesInformation();
    }

    // FIXME generic ion ?
    // FIXME confine ?

    // position
    G4ThreeVector position(fPositionX[fCurrentIndex],
                           fPositionY[fCurrentIndex],
                           fPositionZ[fCurrentIndex]);

    // according to mother volume
    position = fGlobalRotation * position + fGlobalTranslation;

    // direction
    G4ThreeVector momentum_direction(fDirectionX[fCurrentIndex],
                                     fDirectionY[fCurrentIndex],
                                     fDirectionZ[fCurrentIndex]);

    // normalize (needed)
    momentum_direction = momentum_direction / momentum_direction.mag();

    // according to mother volume
    momentum_direction = fGlobalRotation * momentum_direction;

    // energy
    double energy = fEnergy[fCurrentIndex];
    if (energy <= fEnergyThreshold) {
        energy = 0;
        fNumberOfSkippedParticles++;
    }

    // create primary particle
    auto *particle = new G4PrimaryParticle(fParticleDefinition);
    particle->SetKineticEnergy(energy);
    particle->SetMass(fMass);
    particle->SetMomentumDirection(momentum_direction);
    particle->SetCharge(fCharge);

    // time
    double time = current_simulation_time;
    if (fUseTime) {
        if (fUseTimeRelative)
            time += fTime[fCurrentIndex];
        else
            time = fTime[fCurrentIndex];
    }

    // set vertex
    auto *vertex = new G4PrimaryVertex(position, time);
    vertex->SetPrimary(particle);
    event->AddPrimaryVertex(vertex);

    // weights
    if (fUseWeight) {
        event->GetPrimaryVertex(0)->SetWeight(fWeight[fCurrentIndex]);
    }

    fCurrentIndex++;
    fN++;
}
