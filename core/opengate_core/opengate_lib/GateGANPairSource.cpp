/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGANPairSource.h"
#include "G4ParticleTable.hh"
#include "G4UnitsTable.hh"
#include "GateHelpersDict.h"

GateGANPairSource::GateGANPairSource() : GateGANSource() {}

GateGANPairSource::~GateGANPairSource() = default;

void GateGANPairSource::InitializeUserInfo(py::dict &user_info) {
  GateGANSource::InitializeUserInfo(user_info);

  if (fAAManager.IsEnabled()) {
    std::ostringstream oss;
    oss << "Error, cannot use AngularAcceptance with GAN pairs (yet), for the "
           "source '"
        << fName << "'";
    Fatal(oss.str());
  }

  if (fSkipEnergyPolicy == GateAcceptanceAngleTesterManager::AASkipEvent) {
    std::ostringstream oss;
    oss << "Error, cannot use SkipEvent mode with GAN pairs (yet), for the "
           "source '"
        << fName << "'. Use ZeroEnergy";
    Fatal(oss.str());
  }
}

void GateGANPairSource::SetGeneratorInfo(py::dict &user_info) {
  GateGANSource::SetGeneratorInfo(user_info);
  if (!fPosition_is_set_by_GAN) {
    std::ostringstream oss;
    oss << "Error, position must be managed by GAN for a GANPairSource, for "
           "the "
           "source '"
        << fName << "'";
    Fatal(oss.str());
  }
  if (!fDirection_is_set_by_GAN) {
    std::ostringstream oss;
    oss << "Error, direction must be managed by GAN for a GANPairSource, for "
           "the "
           "source '"
        << fName << "'";
    Fatal(oss.str());
  }
  if (!fEnergy_is_set_by_GAN) {
    std::ostringstream oss;
    oss << "Error, energy must be managed by GAN for a GANPairSource, for the "
           "source '"
        << fName << "'";
    Fatal(oss.str());
  }
}

void GateGANPairSource::GeneratePrimaries(G4Event *event,
                                          double current_simulation_time) {
  if (fCurrentIndex >= fCurrentBatchSize)
    GenerateBatchOfParticles();

  // Generate one or two primaries
  GeneratePrimariesPair(event, current_simulation_time);

  // update the index;
  fCurrentIndex++;

  // update the number of generated event
  fNumberOfGeneratedEvents++;
}

void GateGANPairSource::GeneratePrimariesPair(G4Event *event,
                                              double current_simulation_time) {
  // First particle
  GenerateOnePrimary(event, current_simulation_time);

  // position of the second particle
  G4ThreeVector position(fPositionX2[fCurrentIndex], fPositionY2[fCurrentIndex],
                         fPositionZ2[fCurrentIndex]);
  // direction of the second particle
  G4ThreeVector direction(fDirectionX2[fCurrentIndex],
                          fDirectionY2[fCurrentIndex],
                          fDirectionZ2[fCurrentIndex]);

  // move position according to mother volume
  position = fGlobalRotation * position + fGlobalTranslation;
  // normalize (needed)
  direction = direction / direction.mag();
  // move according to mother volume
  direction = fGlobalRotation * direction;

  // energy of the second particle
  double energy = fEnergy2[fCurrentIndex];

  // check if valid
  bool accept_energy =
      energy > fEnergyMinThreshold && energy < fEnergyMaxThreshold;
  if (!accept_energy) {
    energy = 0;
    // at least one of the two vertices has been skipped with zeroE
    fCurrentZeroEvents = 1;
  }

  if (fTime_is_set_by_GAN && accept_energy) {
    // time
    double time = fEffectiveEventTime;
    if (fRelativeTiming)
      time += fTime2[fCurrentIndex];
    else
      time = fTime2[fCurrentIndex];
    // consider the earliest one
    fEffectiveEventTime = min(time, fEffectiveEventTime);
  } else {
    fEffectiveEventTime = current_simulation_time;
  }

  // weights
  double w = 1.0;
  if (fWeight_is_set_by_GAN) {
    w = fWeight2[fCurrentIndex];
  }

  // Vertex
  AddOnePrimaryVertex(event, position, direction, energy, fEffectiveEventTime,
                      w);
}
