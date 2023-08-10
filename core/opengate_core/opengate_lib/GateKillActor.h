/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateKillActor_h
#define GateKillActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateKillActor : public GateVActor {

public:
  // Constructor
  GateKillActor(py::dict &user_info);

  virtual void ActorInitialize();

  // Main function called every step in attached volume
  virtual void SteppingAction(G4Step *);
  virtual void EndSimulationAction();

  // Option: indicate if we need to kill particles
  bool fKillFlag;
};

#endif
