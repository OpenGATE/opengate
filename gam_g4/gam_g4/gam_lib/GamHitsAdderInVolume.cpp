/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitAdderInVolume.h"

GamHitAdderInVolume::GamHitAdderInVolume() {
    fFinalEdep = 0;
    fFinalIndex = 0;
}

void GamHitAdderInVolume::Update(GamHitsAdderActor::AdderPolicy fPolicy,
                                 size_t i,
                                 double edep,
                                 const G4ThreeVector &pos) {
    /*
     * Merge the current hits with the previous ones.
     * EnergyWinnerPosition: keep the position of the one with the largest edep
     * EnergyWeightedCentroidPosition: energy weighted position
     *
     * The final energy is the sum of all edep // FIXME
     * Store the minimal time ? FIXME
     */
    // ignore if no deposited energy
    if (edep == 0) return;
    if (fPolicy == GamHitsAdderActor::AdderPolicy::EnergyWinnerPosition) {
        if (edep > fFinalEdep) {
            fFinalPosition = pos;
            fFinalIndex = i;
        }
    }
    if (fPolicy == GamHitsAdderActor::AdderPolicy::EnergyWeightedCentroidPosition) {
        fFinalPosition += pos * edep;
    }
    fFinalEdep += edep;
}

void GamHitAdderInVolume::Terminate(GamHitsAdderActor::AdderPolicy fPolicy) {
    if (fPolicy == GamHitsAdderActor::AdderPolicy::EnergyWeightedCentroidPosition) {
        if (fFinalEdep != 0)
            fFinalPosition = fFinalPosition / fFinalEdep;
    }
}