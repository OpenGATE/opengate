/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateKillAccordingParticleNameActor_h
#define GateKillAccordingParticleNameActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateKillAccordingParticleNameActor : public GateVActor {

public:
  // Constructor
  GateKillAccordingParticleNameActor(py::dict &user_info);
    struct threadLocalT {
    G4bool fIsAParticleToKill = false;
  };
  G4Cache<threadLocalT> fThreadLocalData;
  std::vector<std::string> fParticlesNameToKill;
  std::vector<G4String> fListOfVolumeAncestor;


  // Main function called every step in attached volume
  void PreUserTrackingAction(const G4Track *) override;
  void SteppingAction(G4Step *) override;
  void InitializeUserInfo(py::dict &user_info) override;

  inline long GetNumberOfKilledParticles() { return fNbOfKilledParticles; }

private:
  long fNbOfKilledParticles = 0;
};

#endif
