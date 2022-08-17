/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include "GateMultiFunctionalDetector.h"
#include "G4VPrimitiveScorer.hh"

GateMultiFunctionalDetector::GateMultiFunctionalDetector(G4String s) : G4MultiFunctionalDetector(s) {

}

GateMultiFunctionalDetector::~GateMultiFunctionalDetector() {
    // In the current G4 G4MultiFunctionalDetector destructor (2021-01-04), there is a loop
    // that delete all primitives before the clear. This seems to lead to seg fault issue
    // during destructor in case of MT
    // The only purpose of this class is to clear the vector of primitives first.

    primitives.clear();
}
