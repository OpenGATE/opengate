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

  void ActorInitialize() override;

  void StartSimulationAction() override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  long fNbOfKilledParticles{};
};

#endif
