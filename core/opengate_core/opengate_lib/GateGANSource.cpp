/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGANSource.h"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "G4UnitsTable.hh"
#include "GateHelpersDict.h"

GateGANSource::GateGANSource() : GateGenericSource() {
  fCurrentIndex = 0;
  fCharge = 0;
  fMass = 0;
  fRelativeTiming = false;
  fEnergyThreshold = -1;
  fPosition_is_set_by_GAN = false;
  fDirection_is_set_by_GAN = false;
  fEnergy_is_set_by_GAN = false;
  fTime_is_set_by_GAN = false;
  fWeight_is_set_by_GAN = false;
  fSkipEnergyPolicy = SEPolicyType::AAUndefined;
}

GateGANSource::~GateGANSource() {}

void GateGANSource::InitializeUserInfo(py::dict &user_info) {
  // the following initialize all GenericSource options
  // and the SPS GateSingleParticleSource
  GateGenericSource::InitializeUserInfo(user_info);

  // Additional specific options for GANSource
  fEnergyThreshold = DictGetDouble(user_info, "energy_threshold");

  // FIXME
  /* FIXME
    - AAManager is already set in GenericSource BUT MUST be iso direction here
    - charge/mass done in GateSingleParticleSource

   */

  // This is done in GateSingleParticleSource
  fCharge = fParticleDefinition->GetPDGCharge();
  fMass = fParticleDefinition->GetPDGMass();

  // set the angle acceptance volume if needed
  auto d = py::dict(user_info["direction"]);
  auto dd = py::dict(d["acceptance_angle"]);
  fAAManager.Initialize(dd, true);
  fSPS->SetAAManager(&fAAManager);

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

  // FIXME generic ion ?
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
  GateVSource::PrepareNextRun();
}

void GateGANSource::SetGeneratorFunction(ParticleGeneratorType &f) {
  fGenerator = f;
}

void GateGANSource::SetGeneratorInfo(py::dict &user_info) {
  // Consider which parameters are set by the GAN or conventional GenericSource
  // sampler
  fPosition_is_set_by_GAN = DictGetBool(user_info, "position_is_set_by_GAN");
  fDirection_is_set_by_GAN = DictGetBool(user_info, "direction_is_set_by_GAN");
  fEnergy_is_set_by_GAN = DictGetBool(user_info, "energy_is_set_by_GAN");
  fTime_is_set_by_GAN = DictGetBool(user_info, "time_is_set_by_GAN");
  fWeight_is_set_by_GAN = DictGetBool(user_info, "weight_is_set_by_GAN");
  fRelativeTiming = DictGetBool(user_info, "timing_is_relative");
  DDD(fPosition_is_set_by_GAN);
  DDD(fDirection_is_set_by_GAN);
  DDD(fEnergy_is_set_by_GAN);
  DDD(fTime_is_set_by_GAN);
  DDD(fWeight_is_set_by_GAN);
  DDD(fRelativeTiming);
}

void GateGANSource::GenerateBatchOfParticles() {
  // I don't know if we should acquire the GIL or not
  // (does not seem needed)
  // py::gil_scoped_acquire acquire;

  // This function (fGenerator) is defined on Python side
  // It fills all values needed for the particles (position, direction, energy,
  // weight)
  fGenerator(this);
  fCurrentIndex = 0;
  // alternative: build vector of G4ThreeVector in GenerateBatchOfParticles
  // (unsure if it is faster)
}

void GateGANSource::GeneratePrimaries(G4Event *event,
                                      double current_simulation_time) {
  // If batch is empty, we generate some particles
  if (fCurrentIndex >= fPositionX.size())
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
  if (fAAManager.IsEnabled())
    return GenerateOnePrimaryWithAA(event, current_simulation_time);

  // If no AA, we loop until energy is acceptable, or we reach the end of the
  // batch Event with energy below the threshold are skipped ( skipped
  G4ThreeVector position;
  G4ThreeVector direction;
  double energy = 0;
  fCurrentZeroEvents = 0;
  fCurrentSkippedEvents = 0;

  while (energy == 0) {
    // position
    // (if it is not set by the GAN, we may avoid to sample at each iteration)
    if (fPosition_is_set_by_GAN or fCurrentSkippedEvents == 0)
      position = GeneratePrimariesPosition();

    // direction
    // (if it is not set by the GAN, we may avoid to sample at each iteration)
    if (fDirection_is_set_by_GAN or fCurrentSkippedEvents == 0)
      direction = GeneratePrimariesDirection();

    // energy
    energy = GeneratePrimariesEnergy();

    // check if the energy is acceptable
    if (energy < fEnergyThreshold) {
      // energy is not ok, but we reach the end of the batch,
      // so we accept with a zeroE event
      if (fCurrentIndex < fEnergy.size() or
          fSkipEnergyPolicy == SEPolicyType::AAZeroEnergy) {
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
  if (energy == -1)
    energy = 0;

  // timing
  auto time = GeneratePrimariesTime(current_simulation_time);

  // weight
  auto weight = GeneratePrimariesWeight();

  // Create the final vertex
  AddOnePrimaryVertex(event, position, direction, energy, time, weight);
}

G4ThreeVector GateGANSource::GeneratePrimariesPosition() {
  G4ThreeVector position;
  if (fPosition_is_set_by_GAN)
    position =
        G4ThreeVector(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
                      fPositionZ[fCurrentIndex]);
  else
    position = fSPS->GetPosDist()->VGenerateOne();
  return position;
}

G4ThreeVector GateGANSource::GeneratePrimariesDirection() {
  G4ThreeVector direction;
  if (fDirection_is_set_by_GAN)
    direction = G4ParticleMomentum(fDirectionX[fCurrentIndex],
                                   fDirectionY[fCurrentIndex],
                                   fDirectionZ[fCurrentIndex]);
  else
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
  if (not fTime_is_set_by_GAN) {
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
  if (fCurrentZeroEvents == 1)
    fEffectiveEventTime = current_simulation_time;
  else
    fEffectiveEventTime += fTime[fCurrentIndex];
  return fEffectiveEventTime;
}

double GateGANSource::GeneratePrimariesWeight() {
  if (fWeight_is_set_by_GAN)
    return fWeight[fCurrentIndex];
  return 1.0;
}

void GateGANSource::GenerateOnePrimaryWithAA(G4Event *event,
                                             double current_simulation_time) {

  Fatal("NOT YET");
}

void GateGANSource::GeneratePrimariesPositionAndDirection(
    G4ThreeVector &position, G4ThreeVector &direction, bool &ezero_direction) {
  DDD("GeneratePrimariesDirection");

  // we use the GAN generated one, with AA rejection
  direction =
      G4ParticleMomentum(fDirectionX[fCurrentIndex], fDirectionY[fCurrentIndex],
                         fDirectionZ[fCurrentIndex]);

  unsigned long skipped = 0;
  fCurrentZeroEvents = 0;
  fCurrentSkippedEvents = 0;
  fAAManager.StartAcceptLoop();
  bool accept_angle = fAAManager.TestIfAccept(position, direction);

  // set to E=0 if angle not ok (when mode is AAZeroEnergy)
  if (fAAManager.GetPolicy() == SEPolicyType::AAZeroEnergy and
      not accept_angle) {
    accept_angle = true;
    skipped = 1;
    ezero_direction = true;
    fCurrentZeroEvents = 1;
  }

  // set to E=0 if energy not ok (when mode is AAZeroEnergy)
  /*if (fSkipEnergyPolicy == SEPolicyType::AAZeroEnergy and
      not accept_energy) {
    accept_angle = true;
    accept_energy = true;
    skipped = 1;
    energy = 0;
    fCurrentZeroEvents = 1;
  }*/

  // loop while not ok
  while (not accept_angle and fCurrentIndex < fEnergy.size()) {
    skipped++;
    fCurrentIndex++;

    // position
    position = GeneratePrimariesPosition();

    // direction
    direction = G4ParticleMomentum(fDirectionX[fCurrentIndex],
                                   fDirectionY[fCurrentIndex],
                                   fDirectionZ[fCurrentIndex]);
    // is angle ok ?
    accept_angle = fAAManager.TestIfAccept(position, direction);

    fCurrentSkippedEvents = skipped;
  }

  // if we reach the end of the batch (fCurrentIndex > fEnergy.size())
  // we still generate the particle with energy == 0 to trigger the generation
  // of another batch
  if (fCurrentIndex >= fEnergy.size())
    ezero_direction = true;
}

/*
// read energy, position and dir
double energy = fEnergy[fCurrentIndex];
G4ThreeVector position(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
                       fPositionZ[fCurrentIndex]);
G4ParticleMomentum momentum_direction(fDirectionX[fCurrentIndex],
                                      fDirectionY[fCurrentIndex],
                                      fDirectionZ[fCurrentIndex]);

// init the AA and check first pos/dir
unsigned long skipped = 0;
fCurrentZeroEvents = 0;
fCurrentSkippedEvents = 0;
fAAManager.

StartAcceptLoop();

bool accept_angle = fAAManager.TestIfAccept(position, momentum_direction);
bool accept_energy = energy > fEnergyThreshold;



// set to E=0 if angle not ok (when mode is AAZeroEnergy)
if (fAAManager.

GetPolicy()

==
SEPolicyType::AAZeroEnergy and
not accept_angle) {
accept_angle = true;
accept_energy = true;
skipped = 1;
energy = 0;
fCurrentZeroEvents = 1;
}

// set to E=0 if energy not ok (when mode is AAZeroEnergy)
if (fSkipEnergyPolicy == SEPolicyType::AAZeroEnergy and
not accept_energy) {
accept_angle = true;
accept_energy = true;
skipped = 1;
energy = 0;
fCurrentZeroEvents = 1;
}

// loop while not ok
while ((not accept_angle or not accept_energy) and
fCurrentIndex<fEnergy.

size()

) {
skipped++;
fCurrentIndex++;

// Read next one
energy = fEnergy[fCurrentIndex];

// position
position =
G4ThreeVector(fPositionX[fCurrentIndex], fPositionY[fCurrentIndex],
              fPositionZ[fCurrentIndex]);

// direction
momentum_direction = G4ParticleMomentum(fDirectionX[fCurrentIndex],
                                        fDirectionY[fCurrentIndex],
                                        fDirectionZ[fCurrentIndex]);
// is angle ok ?
accept_angle = fAAManager.TestIfAccept(position, momentum_direction);

// is energy ok ?
accept_energy = energy > fEnergyThreshold;

fCurrentSkippedEvents = skipped;
}

// if we reach the end of the batch (fCurrentIndex > fEnergy.size())
// we still generate the particle with energy == 0 to trigger the generation
// of another batch
if (fCurrentIndex >= fEnergy.

size()

)
energy = 0;

// time
if (fUseTime) {
if (fRelativeTiming) {
// update the real time (important as the event is in the
// future according to the current_simulation_time)
UpdateEffectiveEventTime(current_simulation_time, fCurrentSkippedEvents
);
if (fCurrentZeroEvents == 1)
fEffectiveEventTime = current_simulation_time;
else
fEffectiveEventTime += fTime[fCurrentIndex];
} else {
fEffectiveEventTime = fTime[fCurrentIndex];
}
}

// weights
double w = 1.0;
if (fUseWeight) {
w = fWeight[fCurrentIndex];
}
GeneratePrimariesAddOne(event, position, momentum_direction, energy,
                        fEffectiveEventTime, w
);
}
*/

void GateGANSource::AddOnePrimaryVertex(G4Event *event, G4ThreeVector position,
                                        G4ThreeVector direction, double energy,
                                        double time, double w) {
  // move position according to mother volume
  position = fGlobalRotation * position + fGlobalTranslation;

  // normalize (needed)
  direction = direction / direction.mag();

  // move according to mother volume
  direction = fGlobalRotation * direction;

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
