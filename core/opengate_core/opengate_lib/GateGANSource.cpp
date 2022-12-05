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
  fAAManager.Initialize(dd, true);
  fSPS->SetAAManager(&fAAManager);

  // energy threshold mode
  auto s = DictGetStr(user_info, "skip_policy");
  fSkipEnergyEventMode = GateAcceptanceAngleTesterManager::AAUndefined;
  if (s == "ZeroEnergy")
    fSkipEnergyEventMode = GateAcceptanceAngleTesterManager::AAZeroEnergy;
  if (s == "SkipEvents")
    fSkipEnergyEventMode = GateAcceptanceAngleTesterManager::AASkipEvent;

  if (fSkipEnergyEventMode == GateAcceptanceAngleTesterManager::AAUndefined) {
    std::ostringstream oss;
    oss << "Unknown '" << s << "' mode for GateAcceptanceAngleTesterManager. "
        << "Expected: ZeroEnergy or SkipEvents";
    Fatal(oss.str());
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
  // (unsure if it is faster)
}

void GateGANSource::GeneratePrimaries(G4Event *event,
                                      double current_simulation_time) {
  if (fCurrentIndex >= fPositionX.size()) {
    GetParticlesInformation();
  }

  // FIXME generic ion ?
  if (fInitGenericIon) {
    Fatal("Sorry, generic ion is not implemented with GAN source");
  }

  // FIXME confine ?
  if (fInitConfine) {
    Fatal("Sorry, confine is not implemented with GAN source");
  }

  if (fIsPaired and fAAManager.IsEnabled()) {
    std::ostringstream oss;
    oss << "Error, cannot use AngularAcceptance with GAN pairs (yet) for "
           "source '"
        << fName << "'";
    Fatal(oss.str());
  }

  if (fIsPaired and
      fSkipEnergyEventMode == GateAcceptanceAngleTesterManager::AASkipEvent) {
    std::ostringstream oss;
    oss << "Error, cannot use SkipEvent mode with GAN pairs (yet) for "
           "source '"
        << fName << "'. Use ZeroEnergy";
    Fatal(oss.str());
  }

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

  /*
    while energy[index] is zero ->  fCurrentIndex++ = n times
    increase the current_simulation_time ! like in PrepareNextTime
    G4PrimaryVertex
   */

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
  fAAManager.StartAcceptLoop();
  bool accept_angle = fAAManager.TestIfAccept(position, momentum_direction);
  bool accept_energy = energy > fEnergyThreshold;

  /*
   * if E : zero, and not angle ?
   */

  // set to E=0 if angle not ok (when mode is AAZeroEnergy)
  if (fAAManager.GetPolicy() ==
          GateAcceptanceAngleTesterManager::AAZeroEnergy and
      not accept_angle) {
    accept_angle = true;
    accept_energy = true;
    skipped = 1;
    energy = 0;
    fCurrentZeroEvents = 1;
  }

  // set to E=0 if energy not ok (when mode is AAZeroEnergy)
  if (fSkipEnergyEventMode == GateAcceptanceAngleTesterManager::AAZeroEnergy and
      not accept_energy) {
    accept_angle = true;
    accept_energy = true;
    skipped = 1;
    energy = 0;
    fCurrentZeroEvents = 1;
  }

  // loop while not ok
  while ((not accept_angle or not accept_energy) and
         fCurrentIndex < fEnergy.size()) {
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
  if (fCurrentIndex >= fEnergy.size())
    energy = 0;

  // time
  if (fUseTime) {
    if (fUseTimeRelative) {
      // update the real time (important as the event is in the
      // future according to the current_simulation_time)
      UpdateEffectiveEventTime(current_simulation_time, fCurrentSkippedEvents);
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
                          fEffectiveEventTime, w);
}

void GateGANSource::GeneratePrimariesPair(G4Event *event,
                                          double current_simulation_time) {
  // First particle
  GeneratePrimariesSingle(event, current_simulation_time);

  // position of the second particle
  G4ThreeVector position(fPositionX2[fCurrentIndex], fPositionY2[fCurrentIndex],
                         fPositionZ2[fCurrentIndex]);
  // direction of the second particle
  G4ThreeVector momentum_direction(fDirectionX2[fCurrentIndex],
                                   fDirectionY2[fCurrentIndex],
                                   fDirectionZ2[fCurrentIndex]);
  // energy of the second particle
  double energy = fEnergy2[fCurrentIndex];

  // check if valid
  bool accept_energy = energy > fEnergyThreshold;
  if (not accept_energy) {
    energy = 0;
    // at least one of the two vertices has been skipped
    fCurrentSkippedEvents = 1;
  }

  // time
  double time = current_simulation_time;
  if (fUseTime) {
    if (fUseTimeRelative) {
      time += fTime2[fCurrentIndex];
    } else {
      time = fTime2[fCurrentIndex];
    }
  }
  if (not accept_energy)
    time = current_simulation_time;
  fEffectiveEventTime =
      min(time, fEffectiveEventTime); // consider the earliest one

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
