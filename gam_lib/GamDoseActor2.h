/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamDoseActor2_h
#define GamDoseActor2_h

#include "G4VPrimitiveScorer.hh"
#include "GamVActor.h"

class GamDoseActor2 : public GamVActor {

public:

    GamDoseActor2() : GamVActor("DoseActor2") {}

    virtual void BeforeStart();

    virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    virtual void SteppingBatchAction() {}


    std::vector<G4ThreeVector> vpositions;
    std::vector<double> vedep;

};

#endif // GamDoseActor2_h
