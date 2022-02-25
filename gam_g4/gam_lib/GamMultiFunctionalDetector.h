/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamMultiFunctionalDetector_h
#define GamMultiFunctionalDetector_h 1

#include "G4MultiFunctionalDetector.hh"

// Re-implementation of G4MultiFunctionalDetector to better control destructor
// It seema that, in MT mode, the primitive should not be deleted by all threads.
class GamMultiFunctionalDetector : public G4MultiFunctionalDetector {

public:

    GamMultiFunctionalDetector(G4String);

    virtual ~GamMultiFunctionalDetector();
};


#endif

