/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateKillAccordingParticleNameLVActor_h
#define GateKillAccordingParticleNameLVActor_h

#include "GateVActor.h"
#include <G4Cache.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateKillAccordingParticleNameLVActor : public GateVActor {

public:
  GateKillAccordingParticleNameLVActor(py::dict &user_info);
  struct threadLocalT {
    G4bool fIsAParticleToKill = false;
    long fNbOfKilledParticles = 0;
  };
  G4Cache<threadLocalT> fThreadLocalData;
  std::vector<std::string> fParticlesNameToKill;
  std::vector<G4String> fListOfVolumeAncestor;

  void StartSimulationAction() override;
  void EndOfSimulationWorkerAction(const G4Run *) override;

  // Selection state is local to each worker; configuration is read-only.
  void PreUserTrackingAction(const G4Track *) override;
  void SteppingAction(G4Step *) override;
  void InitializeUserInfo(py::dict &user_info) override;

  long GetNumberOfKilledParticles() const { return fNbOfKilledParticles; }

private:
  long fNbOfKilledParticles = 0;
};

#endif
