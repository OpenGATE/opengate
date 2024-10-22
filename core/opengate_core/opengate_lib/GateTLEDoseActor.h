/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTLEDoseActor_h
#define GateTLEDoseActor_h

#include "G4Cache.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateDoseActor.h"
#include "itkImage.h"
#include <iostream>
#include <pybind11/stl.h>

#include "G4EmCalculator.hh"
#include "G4NistManager.hh"

namespace py = pybind11;

class GateTLEDoseActor : public GateDoseActor {

public:
  // Constructor
  GateTLEDoseActor(py::dict &user_info);

  void InitializeUserInput(py::dict &user_info) override;

  void InitializeCpp() override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  int EndOfRunActionMasterThread(int run_id) override;

  void BeginOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;
};

#endif // GateTLEDoseActor_h
