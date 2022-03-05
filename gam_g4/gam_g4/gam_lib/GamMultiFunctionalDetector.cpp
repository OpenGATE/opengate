/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include "GamMultiFunctionalDetector.h"
#include "G4VPrimitiveScorer.hh"

GamMultiFunctionalDetector::GamMultiFunctionalDetector(G4String s) : G4MultiFunctionalDetector(s) {

}

GamMultiFunctionalDetector::~GamMultiFunctionalDetector() {
    // In the current G4 G4MultiFunctionalDetector destructor (2021-01-04), there is a loop
    // that delete all primitives before the clear. This seems to lead to seg fault issue
    // during destructor in case of MT
    // The only purpose of this class is to clear the vector of primitives first.

    primitives.clear();
}
