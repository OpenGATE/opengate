/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamARFTrainingDatasetActor_h
#define GamARFTrainingDatasetActor_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHitsCollectionActor.h"
#include "GamHelpers.h"
#include "GamHitsEnergyWindowsActor.h"

namespace py = pybind11;

class GamARFTrainingDatasetActor : public GamHitsCollectionActor {

public:

    // Constructor
    explicit GamARFTrainingDatasetActor(py::dict &user_info);

    // Main function called every step in attached volume
    void StartSimulationAction() override;

    void BeginOfEventAction(const G4Event *event) override;

    void SteppingAction(G4Step *step) override;

    void EndOfEventAction(const G4Event *event) override;

    void EndSimulationAction() override;

    GamHitsEnergyWindowsActor *fEnergyWindowsActor;
    std::string fInputActorName;
    int fRussianRouletteValue;
    double fRussianRouletteFactor;
    GamVHitAttribute *fAtt_E;
    GamVHitAttribute *fAtt_Theta;
    GamVHitAttribute *fAtt_Phi;
    GamVHitAttribute *fAtt_W;

    // During computation
    struct threadLocalT {
        double fE;
        double fTheta;
        double fPhi;
    };
    G4Cache<threadLocalT> fThreadLocalData;

};

#endif // GamARFTrainingDatasetActor_h
