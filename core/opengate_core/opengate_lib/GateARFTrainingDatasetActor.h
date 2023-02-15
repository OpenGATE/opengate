/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateARFTrainingDatasetActor_h
#define GateARFTrainingDatasetActor_h

#include "GateHelpers.h"
#include "GateHitsCollectionActor.h"
#include "GateHitsEnergyWindowsActor.h"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateARFTrainingDatasetActor : public GateHitsCollectionActor {

public:
  // Constructor
  explicit GateARFTrainingDatasetActor(py::dict &user_info);

  // Main function called every step in attached volume
  void StartSimulationAction() override;

  void BeginOfEventAction(const G4Event *event) override;

  void SteppingAction(G4Step *step) override;

  void EndOfEventAction(const G4Event *event) override;

  void EndSimulationAction() override;

  bool fScoreEnergyWindow = false;
  bool fScoreDepositedEnergy = false;
  GateHitsEnergyWindowsActor *fEnergyWindowsActor;
  std::string fEnergyWindowActorName;
  std::string fARFHitsCollectionName;
  std::string fARFHitsCollectionAttribute;
  int fRussianRouletteValue;
  double fRussianRouletteFactor;
  GateVHitAttribute *fAtt_E;
  GateVHitAttribute *fAtt_Theta;
  GateVHitAttribute *fAtt_Phi;
  GateVHitAttribute *fAtt_W;
  GateVHitAttribute *fAtt_Edep;

  // During computation
  struct threadLocalT {
    double fE;
    double fTheta;
    double fPhi;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateARFTrainingDatasetActor_h
