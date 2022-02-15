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

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

protected:
    std::vector<G4ThreeVector> fTranslations;
    std::vector<G4RotationMatrix> fRotations;
    std::string fVolumeName;

};

#endif // GamMotionVolumeActor_h
