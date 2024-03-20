/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSurfaceSplittingActor_h
#define GateSurfaceSplittingActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateSurfaceSplittingActor : public GateVActor {

public:
  // Constructor
  GateSurfaceSplittingActor(py::dict &user_info);

  void ActorInitialize() override;

  void StartSimulationAction() override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  void PreUserTrackingAction(const G4Track *) override;


  G4bool fSplitEnteringParticles =false;
  G4bool fSplitExitingParticles =false ;
  G4int fSplittingFactor;
  G4bool fIsFirstStep;
  G4bool fWeightThreshold;
  G4String fMotherVolumeName;
  std::vector<std::string> fListOfVolumeAncestor;


  long fNbOfKilledParticles{};
};

#endif
