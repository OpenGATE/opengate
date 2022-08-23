/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMultiFunctionalDetector_h
#define GateMultiFunctionalDetector_h 1

#include "G4MultiFunctionalDetector.hh"

// Re-implementation of G4MultiFunctionalDetector to better control destructor
// It seema that, in MT mode, the primitive should not be deleted by all
// threads.
class GateMultiFunctionalDetector : public G4MultiFunctionalDetector {

public:
  GateMultiFunctionalDetector(G4String);

  virtual ~GateMultiFunctionalDetector();
};

#endif
