/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateARFTrainingDatasetActor_h
#define GateARFTrainingDatasetActor_h

#include "GateHelpers.h"
#include "GateVActor.h"
#include "digitizer/GateDigitizerEnergyWindowsActor.h"
#include "digitizer/GateDigitizerHitsCollectionActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateARFTrainingDatasetActor : public GateDigitizerHitsCollectionActor {

public:
  // Constructor
  explicit GateARFTrainingDatasetActor(py::dict &user_info);

  void InitializeUserInput(py::dict &user_info) override;

  // Main function called every step in attached volume
  void StartSimulationAction() override;

  void BeginOfEventAction(const G4Event *event) override;

  void SteppingAction(G4Step *step) override;

  void EndOfEventAction(const G4Event *event) override;

  void EndSimulationAction() override;

  GateDigitizerEnergyWindowsActor *fEnergyWindowsActor;
  std::string fInputActorName;
  int fRussianRouletteValue;
  double fRussianRouletteFactor;
  GateVDigiAttribute *fAtt_E;
  GateVDigiAttribute *fAtt_Theta;
  GateVDigiAttribute *fAtt_Phi;
  GateVDigiAttribute *fAtt_W;

  // During computation
  struct threadLocalT {
    double fE;
    double fTheta;
    double fPhi;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateARFTrainingDatasetActor_h
