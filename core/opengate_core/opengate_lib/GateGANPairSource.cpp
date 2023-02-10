/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGANPairSource.h"
#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GateHelpersDict.h"

GateGANPairSource::GateGANPairSource() : GateGANSource() {}

GateGANPairSource::~GateGANPairSource() {}

void GateGANPairSource::InitializeUserInfo(py::dict &user_info) {
  GateGANSource::InitializeUserInfo(user_info);
  DDD("GateGANPairSource::InitializeUserInf not needed ?");

  if (fAAManager.IsEnabled()) {
    std::ostringstream oss;
    oss << "Error, cannot use AngularAcceptance with GAN pairs (yet) for "
           "source '"
        << fName << "'";
    Fatal(oss.str());
  }

  if (fSkipEnergyPolicy == GateAcceptanceAngleTesterManager::AASkipEvent) {
    std::ostringstream oss;
    oss << "Error, cannot use SkipEvent mode with GAN pairs (yet) for "
           "source '"
        << fName << "'. Use ZeroEnergy";
    Fatal(oss.str());
  }
}

void GateGANPairSource::GeneratePrimaries(G4Event *event,
                                          double current_simulation_time) {
  if (fCurrentIndex >= fPositionX.size())
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
  // FIXME

  double time = current_simulation_time;
  if (fTime_is_set_by_GAN) {
    if (fRelativeTiming) {
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
  if (fWeight_is_set_by_GAN) {
    w = fWeight2[fCurrentIndex];
  }
  AddOnePrimaryVertex(event, position, momentum_direction, energy, time, w);
}
