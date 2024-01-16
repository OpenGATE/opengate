/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGANSource.h"
#include "G4ParticleTable.hh"
#include "G4UnitsTable.hh"
#include "GateHelpersDict.h"

GateGANSource::GateGANSource() : GateGenericSource() {
  fCurrentIndex = INT_MAX;
  fCharge = 0;
  fMass = 0;
  fRelativeTiming = false;
  fEnergyMinThreshold = -1;
  fEnergyMaxThreshold = FLT_MAX;
  fPosition_is_set_by_GAN = false;
  fDirection_is_set_by_GAN = false;
  fEnergy_is_set_by_GAN = false;
  fTime_is_set_by_GAN = false;
  fWeight_is_set_by_GAN = false;
  fSkipEnergyPolicy = SEPolicyType::AAUndefined;
  fCurrentBatchSize = 0;
  fCurrentBatchSize = 0;
  fTotalZeroEvents = 0;
  fTotalSkippedEvents = 0;
  fCurrentSkippedEvents = 0;
  fCurrentZeroEvents = 0;
}

GateGANSource::~GateGANSource() = default;

void GateGANSource::InitializeUserInfo(py::dict &user_info) {
  // the following initialize all GenericSource options
  // and the SPS GateSingleParticleSource
  GateGenericSource::InitializeUserInfo(user_info);

  // Batch size
  fCurrentBatchSize = DictGetInt(user_info, "batch_size");

  // Additional specific options for GANSource
  fEnergyMinThreshold = DictGetDouble(user_info, "energy_min_threshold");
  fEnergyMaxThreshold = DictGetDouble(user_info, "energy_max_threshold");

  // This is done in GateSingleParticleSource, but we need charge/mass later
  fCharge = fParticleDefinition->GetPDGCharge();
  fMass = fParticleDefinition->GetPDGMass();

  // set the angle acceptance volume if needed
  // AAManager is already set in GenericSource BUT MUST be iso direction here ?
  auto d = py::dict(user_info["direction"]);
  auto dd = py::dict(d["acceptance_angle"]);
  auto &l = fThreadLocalDataAA.Get();
  l.fAAManager->Initialize(dd, true);
  fSPS->SetAAManager(l.fAAManager);

  // energy threshold mode
  auto s = DictGetStr(user_info, "skip_policy");
  fSkipEnergyPolicy = SEPolicyType::AAUndefined;
  if (s == "ZeroEnergy")
    fSkipEnergyPolicy = SEPolicyType::AAZeroEnergy;
  if (s == "SkipEvents")
    fSkipEnergyPolicy = SEPolicyType::AASkipEvent;

  if (fSkipEnergyPolicy == SEPolicyType::AAUndefined) {
    std::ostringstream oss;
    oss << "Unknown '" << s << "' mode for GateAcceptanceAngleTesterManager. "
        << "Expected: ZeroEnergy or SkipEvents";
    Fatal(oss.str());
  }

  // FIXME generic ion ? Should be possible, not tested
  if (fInitGenericIon) {
    Fatal("Sorry, generic ion is not implemented with GAN source");
  }

  // FIXME confine ?
  if (fInitConfine) {
    Fatal("Sorry, confine is not implemented with GAN source");
  }
}

void GateGANSource::PrepareNextRun() {
  // needed to update orientation wrt mother volume
  // (no need to update th fSPS pos in GateGenericSource)
  // GateVSource::PrepareNextRun();
  // FIXME remove this function ?
  // GateGenericSource::PrepareNextRun();
  GateVSource::PrepareNextRun();
  // This global transformation is given to the SPS that will
  // generate particles in the correct coordinate system
  auto &l = fThreadLocalData.Get();
  auto *pos = fSPS->GetPosDist();
  pos->SetCentreCoords(l.fGlobalTranslation);

  // orientation according to mother volume
  auto rotation = l.fGlobalRotation;
  G4ThreeVector r1(rotation(0, 0), rotation(1, 0), rotation(2, 0));
  G4ThreeVector r2(rotation(0, 1), rotation(1, 1), rotation(2, 1));
  pos->SetPosRot1(r1);
  pos->SetPosRot2(r2);
}

void GateGANSource::SetGeneratorFunction(ParticleGeneratorType &f) {
  fGenerator = f;
}

void GateGANSource::SetGeneratorInfo(py::dict &user_info) {
  // Consider which parameters are set by the GAN
  // or conventional GenericSource sampler
  fPosition_is_set_by_GAN = DictGetBool(user_info, "position_is_set_by_GAN");
  fDirection_is_set_by_GAN = DictGetBool(user_info, "direction_is_set_by_GAN");
  fEnergy_is_set_by_GAN = DictGetBool(user_info, "energy_is_set_by_GAN");
  fTime_is_set_by_GAN = DictGetBool(user_info, "time_is_set_by_GAN");
  fWeight_is_set_by_GAN = DictGetBool(user_info, "weight_is_set_by_GAN");
  fRelativeTiming = DictGetBool(user_info, "timing_is_relative");
}

void GateGANSource::GenerateBatchOfParticles() {
  // I don't know if we should acquire the GIL or not
  // (does not seem needed)
  // py::gil_scoped_acquire acquire;

  // This function (fGenerator) is defined on Python side
  // It fills all values needed for the particles (position, dir, energy, etc)
  // Alternative: build vector of G4ThreeVector in GenerateBatchOfParticles ?
  // (unsure if it is faster)
  fGenerator(this);
  fCurrentIndex = 0;

  // Then, we need to get the exact number of particle in the batch.
  // It depends on what is managed by the GAN
  if (fPosition_is_set_by_GAN) {
    fCurrentBatchSize = fPositionX.size();
    return;
  }
  if (fEnergy_is_set_by_GAN) {
    fCurrentBatchSize = fEnergy.size();
    return;
  }
  if (fDirection_is_set_by_GAN) {
    fCurrentBatchSize = fDirectionX.size();
    return;
  }
  if (fTime_is_set_by_GAN) {
    fCurrentBatchSize = fTime.size();
    return;
  }
}

void GateGANSource::GeneratePrimaries(G4Event *event,
                                      double current_simulation_time) {

  // If batch is empty, we generate some particles
  if (fCurrentIndex >= fCurrentBatchSize)
    GenerateBatchOfParticles();

  // Go
  GenerateOnePrimary(event, current_simulation_time);

  // update the index;
  fCurrentIndex++;

  // update the number of generated event
  fNumberOfGeneratedEvents++;
}

void GateGANSource::GenerateOnePrimary(G4Event *event,
                                       double current_simulation_time) {
  // If AA (Angular Acceptance) is enabled, we perform rejection
  auto &l = fThreadLocalDataAA.Get();
  if (l.fAAManager->IsEnabled())
    return GenerateOnePrimaryWithAA(event, current_simulation_time);

  // If no AA, we loop until energy is acceptable,
  // or when we reach the end of the batch Event
  G4ThreeVector position;
  G4ThreeVector direction;
  double energy = 0;
  fCurrentZeroEvents = 0;
  fCurrentSkippedEvents = 0;

  while (energy == 0 && fCurrentIndex < fCurrentBatchSize) {
    // position
    // (if it is not set by the GAN, we may avoid to sample at each iteration)
    if (fPosition_is_set_by_GAN || fCurrentSkippedEvents == 0)
      position = GeneratePrimariesPosition();
    // FIXME change position is not set by GAN

    // direction
    // (if it is not set by the GAN, we may avoid to sample at each iteration)
    if (fDirection_is_set_by_GAN || fCurrentSkippedEvents == 0)
      direction = GeneratePrimariesDirection();

    // energy
    energy = GeneratePrimariesEnergy();

    // check if the energy is acceptable
    if (energy < fEnergyMinThreshold || energy > fEnergyMaxThreshold) {
      // energy is not ok, we skip or create a ZeroEnergy event
      // if we reach the end of the batch, we create zeroE event
      if (fSkipEnergyPolicy == SEPolicyType::AAZeroEnergy ||
          fCurrentIndex >= fCurrentBatchSize - 1) {
        energy = -1;
        fCurrentZeroEvents = 1;
      } else {
        // energy is not ok, we skip the event and try the next one
        energy = 0;
        fCurrentSkippedEvents++;
        fCurrentIndex++;
      }
    }
  }

  // If the end of the batch is reached, or if skip policy is zero_energy
  // we continue with a zeroE event
  if (energy == -1 || fCurrentIndex >= fCurrentBatchSize - 1) {
    energy = 0;
    fCurrentZeroEvents = 1;
  }

  // timing
  auto time = GeneratePrimariesTime(current_simulation_time);

  // weight
  auto weight = GeneratePrimariesWeight();

  // Create the final vertex
  AddOnePrimaryVertex(event, position, direction, energy, time, weight);
}

G4ThreeVector GateGANSource::GeneratePrimariesPosition() {
  G4ThreeVector position;
  if (fPosition_is_set_by_GAN) {
    position =
        G4ThreeVector(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
                      fPositionZ[fCurrentIndex]);
    position = fLocalRotation * position + fLocalTranslation; // FIXME
    // move position according to mother volume
    auto &l = fThreadLocalData.Get();
    position = l.fGlobalRotation * position + l.fGlobalTranslation;
  } else
    position = fSPS->GetPosDist()->VGenerateOne();
  return position;
}

G4ThreeVector GateGANSource::GeneratePrimariesDirection() {
  G4ThreeVector direction;
  if (fDirection_is_set_by_GAN) {
    direction = G4ParticleMomentum(fDirectionX[fCurrentIndex],
                                   fDirectionY[fCurrentIndex],
                                   fDirectionZ[fCurrentIndex]);
    // normalize (needed)
    direction = direction / direction.mag();
    // move according to mother volume
    auto &l = fThreadLocalData.Get();
    direction = l.fGlobalRotation * direction;
  } else
    direction = fSPS->GetAngDist()->GenerateOne();
  return direction;
}

double GateGANSource::GeneratePrimariesEnergy() {
  double energy;
  if (fEnergy_is_set_by_GAN)
    energy = fEnergy[fCurrentIndex];
  else
    energy = fSPS->GetEneDist()->VGenerateOne(fParticleDefinition);
  return energy;
}

double GateGANSource::GeneratePrimariesTime(double current_simulation_time) {
  if (!fTime_is_set_by_GAN) {
    fEffectiveEventTime = current_simulation_time;
    return fEffectiveEventTime;
  }

  if (fCurrentZeroEvents > 0) {
    fEffectiveEventTime = current_simulation_time;
    return fEffectiveEventTime;
  }

  // if the time is managed by the GAN, it can be relative or absolute.
  if (fRelativeTiming) {
    // update the real time (important as the event is in the
    // future according to the current_simulation_time)
    UpdateEffectiveEventTime(current_simulation_time, fCurrentSkippedEvents);
  }

  // Get the time from the GAN except if it is a zeroE
  if (fCurrentZeroEvents > 0)
    fEffectiveEventTime = current_simulation_time;
  else {
    if (fRelativeTiming)
      fEffectiveEventTime += fTime[fCurrentIndex];
    else
      fEffectiveEventTime = fTime[fCurrentIndex];
  }
  return fEffectiveEventTime;
}

double GateGANSource::GeneratePrimariesWeight() {
  if (fWeight_is_set_by_GAN)
    return fWeight[fCurrentIndex];
  return 1.0;
}

void GateGANSource::GenerateOnePrimaryWithAA(G4Event *event,
                                             double current_simulation_time) {
  G4ThreeVector position;
  G4ThreeVector direction;
  double energy = 0;
  fCurrentZeroEvents = 0;
  fCurrentSkippedEvents = 0;
  bool cont = true;
  auto &l = fThreadLocalDataAA.Get();
  l.fAAManager->StartAcceptLoop();

  while (cont) {
    // position
    position = GeneratePrimariesPosition();

    // direction
    direction = GeneratePrimariesDirection();

    // check AA
    bool accept_angle = l.fAAManager->TestIfAccept(position, direction);

    if (!accept_angle && l.fAAManager->GetPolicy() ==
                             GateAcceptanceAngleTesterManager::AAZeroEnergy) {
      energy = 0;
      cont = false;
      continue; // stop here
    }
    if (!accept_angle && l.fAAManager->GetPolicy() ==
                             GateAcceptanceAngleTesterManager::AASkipEvent) {
      fCurrentSkippedEvents++;
      fCurrentIndex++;
      continue; // no need to check energy now
    }

    // energy
    energy = GeneratePrimariesEnergy();

    // check if the energy is acceptable
    if (energy < fEnergyMinThreshold || energy > fEnergyMaxThreshold) {
      // energy is not ok, we skip or create a ZeroEnergy event
      // if we reach the end of the batch, we create zeroE event
      if (fSkipEnergyPolicy == SEPolicyType::AAZeroEnergy) {
        cont = false;
        energy = 0;
        fCurrentZeroEvents = 1;
        continue; // stop here
      } else {
        // energy is not ok, we skip the event and try the next one
        fCurrentSkippedEvents++;
        fCurrentIndex++;
      }
    }

    // check index
    if (fCurrentIndex >= fCurrentBatchSize) {
      cont = false;
      energy = 0;
      fCurrentZeroEvents = 1;
      continue; // stop here
    } else {
      cont = false;
    }
  }

  // timing
  auto time = GeneratePrimariesTime(current_simulation_time);

  // weight
  auto weight = GeneratePrimariesWeight();

  // Create the final vertex
  AddOnePrimaryVertex(event, position, direction, energy, time, weight);
}

void GateGANSource::AddOnePrimaryVertex(G4Event *event,
                                        const G4ThreeVector &position,
                                        const G4ThreeVector &direction,
                                        double energy, double time, double w) {
  // create primary particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(direction);
  particle->SetCharge(fCharge);

  // set vertex
  auto *vertex = new G4PrimaryVertex(position, time);
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);

  // weights
  event->GetPrimaryVertex(0)->SetWeight(w);
}
