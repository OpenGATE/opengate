/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateKillInteractingParticleActor_h
#define GateKillInteractingParticleActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateKillInteractingParticleActor : public GateVActor {

public:
  // Constructor
  GateKillInteractingParticleActor(py::dict &user_info);


  void StartSimulationAction() override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  void PreUserTrackingAction(const G4Track *) override;

  std::vector<G4String> fParticlesTypeToKill;
  G4double fKineticEnergyAtTheEntrance = 0;
  G4int ftrackIDAtTheEntrance = 0;
  G4bool fIsFirstStep = true;
  std::vector<std::string> fListOfVolumeAncestor;

  long fNbOfKilledParticles{};
};

#endif
