/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitAdderInVolume_h
#define GamHitAdderInVolume_h

#include "GamHitsAdderActor.h"

/*
* TODO
 */

class GamHitAdderInVolume {
public:

    GamHitAdderInVolume();

    double fFinalEdep = 0;
    G4ThreeVector fFinalPosition;
    size_t fFinalIndex = 0;

    void Update(GamHitsAdderActor::AdderPolicy fPolicy, size_t i, double edep, const G4ThreeVector &pos);

    void Terminate(GamHitsAdderActor::AdderPolicy fPolicy);
};


#endif // GamHitAdderInVolume_h
