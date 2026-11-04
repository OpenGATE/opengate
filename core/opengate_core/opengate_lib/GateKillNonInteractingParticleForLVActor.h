/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateKillNonInteractingParticleForLVActor_h
#define GateKillNonInteractingParticleForLVActor_h

#include "GateVActor.h"
#include <G4Cache.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

// LV contribution selection using the existing entrance/exit energy criterion.
class GateKillNonInteractingParticleForLVActor : public GateVActor {
public:
  explicit GateKillNonInteractingParticleForLVActor(py::dict &user_info);

  void StartSimulationAction() override;
  void PreUserTrackingAction(const G4Track *) override;
  void SteppingAction(G4Step *) override;
  void EndOfSimulationWorkerAction(const G4Run *) override;

  long GetNumberOfKilledParticles() const { return fNbOfKilledParticles; }

  // Configured before transport; read-only across workers.
  std::vector<std::string> fListOfVolumeAncestor;

  struct WorkerState {
    G4bool fPassedByTheMotherVolume = false;
    G4double fKineticEnergyAtTheEntrance = 0;
    G4int fTrackIDAtTheEntrance = 0;
    G4bool fIsFirstStep = true;
    long fNbOfKilledParticles = 0;
  };
  G4Cache<WorkerState> fWorkerState;

private:
  long fNbOfKilledParticles = 0;
};

#endif
