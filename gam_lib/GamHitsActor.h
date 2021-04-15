/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsActor_h
#define GamHitsActor_h

#include <pybind11/stl.h>
#include "G4GenericAnalysisManager.hh"
#include "GamVActor.h"
#include "GamHelpers.h"

namespace py = pybind11;

struct FillStepStruct;
typedef std::function<void(G4GenericAnalysisManager *, FillStepStruct &,
                           G4Step *, G4TouchableHistory *)> StepFillFunction;

typedef struct FillStepStruct {
    std::string name;
    char type;
    unsigned int i;
    StepFillFunction fill;
    bool enabled = false;
} FillStepStruct;

#define STEP_FILL_FUNCTION [=](G4GenericAnalysisManager *am, FillStepStruct &e, G4Step *step, G4TouchableHistory * )

class GamHitsActor : public GamVActor {

public:

    //explicit GamHitsActor(std::string type_name);
    explicit GamHitsActor(py::dict &user_info);

    virtual ~GamHitsActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    // Called every time a Track starts (all threads)
    virtual void PreUserTrackingAction(const G4Track *track);

    // Called every time a batch of step must be processed
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    std::vector<std::string> fStepFillNames;

protected:
    void BuildAvailableElements();

    void AddFillStepElement(std::string name, char type, StepFillFunction f);

    std::vector<FillStepStruct> fStepFillEnabledElements;
    std::vector<FillStepStruct> fStepFillAllElements;
    std::string fOutputFilename;

};

#endif // GamHitsActor_h
