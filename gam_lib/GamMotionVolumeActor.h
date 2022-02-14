/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamMotionVolumeActor_h
#define GamMotionVolumeActor_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHitsCollection.h"

namespace py = pybind11;

class GamMotionVolumeActor : public GamVActor {

public:

    explicit GamMotionVolumeActor(py::dict &user_info);

    virtual ~GamMotionVolumeActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    // Called by every worker when the simulation is about to end
    virtual void EndOfSimulationWorkerAction(const G4Run * /*lastRun*/);

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();


protected:
    std::vector<G4ThreeVector> fTranslations;
    std::vector<G4RotationMatrix> fRotations;

};

#endif // GamMotionVolumeActor_h
