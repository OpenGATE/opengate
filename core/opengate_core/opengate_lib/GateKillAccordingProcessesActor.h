/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateKillAccordingProcessesActor_h
#define GateKillAccordingProcessesActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateKillAccordingProcessesActor : public GateVActor {

public:
  // Constructor
  GateKillAccordingProcessesActor(py::dict &user_info);
  std::vector<G4String> GetListOfPhysicsListProcesses();

  void InitializeUserInfo(py::dict &user_info) override;

  void BeginOfRunAction(const G4Run *) override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  void PreUserTrackingAction(const G4Track *) override;

  std::vector<G4String> fParticlesTypeToKill;
  G4double fKineticEnergyAtTheEntrance = 0;
  G4int ftrackIDAtTheEntrance = 0;
  G4bool fIsFirstStep = true;
  std::vector<std::string> fProcessesToKillIfOccurence;
  std::vector<std::string> fProcessesToKillIfNoOccurence;
  G4bool fKill = true;
  std::vector<std::string> fListOfVolumeAncestor;

  long fNbOfKilledParticles{};
};

#endif
