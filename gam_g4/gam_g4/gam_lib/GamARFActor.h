/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamARFActor_h
#define GamARFActor_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHelpers.h"

namespace py = pybind11;

class GamARFActor : public GamVActor {

public:

    // Callback function
    using ARFFunctionType = std::function<void(GamARFActor *)>;

    // Constructor
    GamARFActor(py::dict &user_info);

    virtual void ActorInitialize();

    // Main function called every step in attached volume
    virtual void SteppingAction(G4Step *);

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called when the simulation end
    virtual void EndSimulationAction();

    void SetARFFunction(ARFFunctionType &f);

    // need public because exposed to Python
    std::vector<double> fEnergy;
    std::vector<double> fPositionX;
    std::vector<double> fPositionY;
    std::vector<double> fDirectionX;
    std::vector<double> fDirectionY;

    // FIXME multithreading ???
    int fCurrentNumberOfHits;

protected:

    int fBatchSize;
    ARFFunctionType fApply;

};

#endif // GamARFActor_h
