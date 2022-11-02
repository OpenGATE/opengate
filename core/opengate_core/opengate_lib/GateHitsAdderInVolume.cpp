/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitsAdderInVolume.h"

GateHitsAdderInVolume::GateHitsAdderInVolume() {
  fFinalEdep = 0.0;
  fFinalIndex = 0;
  fFinalTime = DBL_MAX;
}

void GateHitsAdderInVolume::Update(GateHitsAdderActor::AdderPolicy fPolicy,
                                   size_t i, double edep,
                                   const G4ThreeVector &pos, double time) {
  /*
   * Merge the current hits with the previous ones.

   * EnergyWinnerPosition: keep the position of the one with the largest edep
   * EnergyWeightedCentroidPosition: energy weighted position

   * The final energy is the sum of all edep
   * Store the minimal time (earliest)

   */
  // ignore if no deposited energy
  if (edep == 0)
    return;

  if (fPolicy == GateHitsAdderActor::AdderPolicy::EnergyWinnerPosition) {
    if (edep > fMaxEdep) {
      fFinalPosition = pos;
      fFinalIndex = i;
      fMaxEdep = edep;
    }
  }

  if (fPolicy ==
      GateHitsAdderActor::AdderPolicy::EnergyWeightedCentroidPosition) {
    fFinalPosition += pos * edep;
  }

  // The final energy is the sum of all edep
  fFinalEdep += edep;

  // The final time is the one of the earliest hit
  if (time < fFinalTime)
    fFinalTime = time;
}

void GateHitsAdderInVolume::Terminate(GateHitsAdderActor::AdderPolicy fPolicy) {
  if (fPolicy ==
      GateHitsAdderActor::AdderPolicy::EnergyWeightedCentroidPosition) {
    if (fFinalEdep != 0)
      fFinalPosition = fFinalPosition / fFinalEdep;
  }
}
