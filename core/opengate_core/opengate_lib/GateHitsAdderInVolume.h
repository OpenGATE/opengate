/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitAdderInVolume_h
#define GateHitAdderInVolume_h

#include "GateHitsAdderActor.h"

/*
    Helper class used by GateHitsAdderActor
 */

class GateHitsAdderInVolume {
public:

    GateHitsAdderInVolume();

    double fFinalEdep = 0;
    double fFinalTime = 0;
    G4ThreeVector fFinalPosition;
    size_t fFinalIndex = 0;

    void Update(GateHitsAdderActor::AdderPolicy fPolicy, size_t i, double edep, const G4ThreeVector &pos, double time);

    void Terminate(GateHitsAdderActor::AdderPolicy fPolicy);
};

#endif // GateHitAdderInVolume_h
