/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGANSource.h"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpersDict.h"

GateGANSource::GateGANSource() : GateGenericSource() {
  fCurrentIndex = 0;
  // for debug, we count the number of E<=0
  fNumberOfSkippedParticles = 0;
  fCharge = 0;
  fMass = 0;
  fUseWeight = false; // set from py side
  fUseTime = false;   // set from py side
  fUseTimeRelative = false;
  fEnergyThreshold = -1;
}

GateGANSource::~GateGANSource() {}

void GateGANSource::InitializeUserInfo(py::dict &user_info) {
  GateGenericSource::InitializeUserInfo(user_info);
  fEnergyThreshold = DictGetDouble(user_info, "energy_threshold");
  fIsPaired = DictGetBool(user_info, "is_paired");

  fCharge = fParticleDefinition->GetPDGCharge();
  fMass = fParticleDefinition->GetPDGMass();

  // set the angle acceptance volume if needed
  auto d = py::dict(user_info["direction"]);
  auto dd = py::dict(d["acceptance_angle"]);
  fSPS = new GateSingleParticleSource(fMother);
  fSPS->SetAcceptanceAngleParam(dd);
}

void GateGANSource::PrepareNextRun() {
  // needed to update orientation wrt mother volume
  GateVSource::PrepareNextRun();
}

void GateGANSource::SetGeneratorFunction(ParticleGeneratorType &f) {
  fGenerator = f;
}

void GateGANSource::GetParticlesInformation() {
  // I don't know if we should acquire the GIL or not
  // (does not seem needed)
  // py::gil_scoped_acquire acquire;

  // This function (fGenerator) is defined on Python side
  // It fills all values needed for the particles (position, direction, energy,
  // weight)
  fGenerator(this);
  fCurrentIndex = 0;
  // alternative: build vector of G4ThreeVector in GetParticlesInformation
  // (unsure if faster)
}

void GateGANSource::GeneratePrimaries(G4Event *event,
                                      double current_simulation_time) {
  if (fCurrentIndex >= fPositionX.size()) {
    GetParticlesInformation();
  }

  // FIXME generic ion ?
  // FIXME confine ?

  // Generate one or two primaries
  if (fIsPaired)
    GeneratePrimariesPair(event, current_simulation_time);
  else
    GeneratePrimariesSingle(event, current_simulation_time);

  // update the index;
  fCurrentIndex++;

  // update the number of generated event
  fNumberOfGeneratedEvents++;
}

void GateGANSource::GeneratePrimariesSingle(G4Event *event,
                                            double current_simulation_time) {
  // position
  G4ThreeVector position(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
                         fPositionZ[fCurrentIndex]);

  // direction
  G4ThreeVector momentum_direction(fDirectionX[fCurrentIndex],
                                   fDirectionY[fCurrentIndex],
                                   fDirectionZ[fCurrentIndex]);

  // energy
  double energy = fEnergy[fCurrentIndex];

  // time
  double time = current_simulation_time;
  if (fUseTime) {
    if (fUseTimeRelative) {
      time += fTime[fCurrentIndex];
    } else {
      time = fTime[fCurrentIndex];
    }
  }

  // weights
  double w = 1.0;
  if (fUseWeight) {
    w = fWeight[fCurrentIndex];
  }
  GeneratePrimariesAddOne(event, position, momentum_direction, energy, time, w);
}

void GateGANSource::GeneratePrimariesPair(G4Event *event,
                                          double current_simulation_time) {
  // First particle
  GeneratePrimariesSingle(event, current_simulation_time);

  // Second particle

  // position
  G4ThreeVector position(fPositionX2[fCurrentIndex], fPositionY2[fCurrentIndex],
                         fPositionZ2[fCurrentIndex]);
  // direction
  G4ThreeVector momentum_direction(fDirectionX2[fCurrentIndex],
                                   fDirectionY2[fCurrentIndex],
                                   fDirectionZ2[fCurrentIndex]);
  // energy
  double energy = fEnergy2[fCurrentIndex];

  // time
  double time = current_simulation_time;
  if (fUseTime) {
    if (fUseTimeRelative) {
      time += fTime2[fCurrentIndex];
    } else {
      time = fTime2[fCurrentIndex];
    }
  }

  // weights
  double w = 1.0;
  if (fUseWeight) {
    w = fWeight2[fCurrentIndex];
  }
  GeneratePrimariesAddOne(event, position, momentum_direction, energy, time, w);
}

void GateGANSource::GeneratePrimariesAddOne(G4Event *event,
                                            G4ThreeVector position,
                                            G4ThreeVector momentum_direction,
                                            double energy, double time,
                                            double w) {
  // move position according to mother volume
  position = fGlobalRotation * position + fGlobalTranslation;

  // normalize (needed)
  momentum_direction = momentum_direction / momentum_direction.mag();

  // move according to mother volume
  momentum_direction = fGlobalRotation * momentum_direction;

  // energy
  if (energy <= fEnergyThreshold) {
    energy = 0;
    fNumberOfSkippedParticles++;
  }

  // Accept angle ?
  bool accept = fSPS->TestIfAcceptAngle(position, momentum_direction);
  if (not accept) {
    energy = 0;
  }

  // create primary particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(momentum_direction);
  particle->SetCharge(fCharge);

  // set vertex
  auto *vertex = new G4PrimaryVertex(position, time);
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);

  // weights
  if (fUseWeight) {
    event->GetPrimaryVertex(0)->SetWeight(w);
  }
}
