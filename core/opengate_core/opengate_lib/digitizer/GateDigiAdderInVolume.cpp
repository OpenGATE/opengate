/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAdderInVolume.h"
#include "G4UnitsTable.hh"

GateDigiAdderInVolume::GateDigiAdderInVolume() {
  fFinalEdep = 0.0;
  fFinalIndex = 0;
  fFinalTime = DBL_MAX;
  fNumberOfHits = 0;
  fTimeDifferenceFlag = false;
  fNumberOfHitsFlag = false;
  fPolicy = GateDigitizerAdderActor::AdderPolicy::Error;
}

GateDigiAdderInVolume::GateDigiAdderInVolume(
    GateDigitizerAdderActor::AdderPolicy policy, bool timeDifferenceFlag,
    bool numberOfHitsFlag)
    : GateDigiAdderInVolume() {
  fTimeDifferenceFlag = timeDifferenceFlag;
  fPolicy = policy;
  fNumberOfHitsFlag = numberOfHitsFlag;
}

void GateDigiAdderInVolume::Update(size_t i, double edep,
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

  if (fPolicy == GateDigitizerAdderActor::AdderPolicy::EnergyWinnerPosition) {
    if (edep > fMaxEdep) {
      fFinalPosition = pos;
      fFinalIndex = i;
      fMaxEdep = edep;
    }
  }

  if (fPolicy ==
      GateDigitizerAdderActor::AdderPolicy::EnergyWeightedCentroidPosition) {
    fFinalPosition += pos * edep;
  }

  // The final energy is the sum of all edep
  fFinalEdep += edep;

  // The final time is the one of the earliest hit
  if (time < fFinalTime)
    fFinalTime = time;

  // option: store max time difference
  if (fTimeDifferenceFlag) {
    if (time < fEarliestTime)
      fEarliestTime = time;
    if (time > fLatestTime)
      fLatestTime = time;
  }

  // option: store the number of hits
  if (fNumberOfHitsFlag)
    fNumberOfHits++;
}

void GateDigiAdderInVolume::Terminate() {
  if (fPolicy ==
      GateDigitizerAdderActor::AdderPolicy::EnergyWeightedCentroidPosition) {
    if (fFinalEdep != 0)
      fFinalPosition = fFinalPosition / fFinalEdep;
  }
  if (fTimeDifferenceFlag) {
    fDifferenceTime = fLatestTime - fEarliestTime;
  }
}
