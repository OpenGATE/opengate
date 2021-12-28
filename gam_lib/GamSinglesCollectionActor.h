/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSinglesCollectionActor_h
#define GamSinglesCollectionActor_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHitsCollection.h"

namespace py = pybind11;

class GamSinglesCollectionActor : public GamVActor {

public:

    explicit GamSinglesCollectionActor(py::dict &user_info);

    virtual ~GamSinglesCollectionActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    // Called every time a Event starts (all threads)
    virtual void BeginOfEventAction(const G4Event *event);

    // Called every time a Event endss (all threads)
    virtual void EndOfEventAction(const G4Event *event);

protected:
    std::string fOutputFilename;
    std::string fSinglesCollectionName;
    GamHitsCollection * fSingles;
    GamHitsCollection * fHits;

    int fIndex;

};

#endif // GamSinglesCollectionActor_h
