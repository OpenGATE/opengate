/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GAM_G4_GAMHITSPROJECTIONACTOR_H
#define GAM_G4_GAMHITSPROJECTIONACTOR_H

#include <pybind11/stl.h>
#include "G4Cache.hh"
#include "GamVActor.h"
#include "GamHitsCollection.h"
#include "GamHitsHelpers.h"
#include "itkImage.h"

namespace py = pybind11;

/*
 * Actor that create some projections (2D images) from several Hits Collections in the same volume.
 */

class GamHitsProjectionActor : public GamVActor {

public:

    explicit GamHitsProjectionActor(py::dict &user_info);

    virtual ~GamHitsProjectionActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time an Event ends (all threads)
    virtual void EndOfEventAction(const G4Event *event);

    // Image type is 3D float by default
    typedef itk::Image<float, 3> ImageType;
    ImageType::Pointer fImage;

protected:
    std::string fOutputFilename;
    std::vector<std::string> fInputHitsCollectionNames;
    std::vector<GamHitsCollection *> fInputHitsCollections;

    void ProcessSlice(size_t slice, size_t channel);

    G4ThreeVector fPreviousTranslation;
    G4RotationMatrix fPreviousRotation;

    // During computation
    struct threadLocalT {
        std::vector<std::vector<G4ThreeVector> *> fInputPos;
        std::vector<size_t> fIndex;
    };
    G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GAM_G4_GAMHITSPROJECTIONACTOR_H
