/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateKillParticlesNotCrossingMaterialsActor_h
#define GateKillParticlesNotCrossingMaterialsActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateKillParticlesNotCrossingMaterialsActor : public GateVActor {

public:
  // Constructor
  GateKillParticlesNotCrossingMaterialsActor(py::dict &user_info);

  void PreUserTrackingAction(const G4Track*) override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  void InitializeUserInfo(py::dict &user_info) override;
  std::vector<std::string> fListOfVolumeAncestor;




private:
  std::vector<std::string> fMaterialsSparingParticles;
  G4bool fKillParticle;
};

#endif
