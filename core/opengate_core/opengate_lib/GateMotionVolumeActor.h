/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMotionVolumeActor_h
#define GateMotionVolumeActor_h

#include <pybind11/stl.h>
#include "GateVActor.h"
#include "GateHitsCollection.h"

namespace py = pybind11;

class GateMotionVolumeActor : public GateVActor {

public:

    explicit GateMotionVolumeActor(py::dict &user_info);

    virtual ~GateMotionVolumeActor();

    // Called every time a Run is about to starts in the Master (MT only)
    virtual void PrepareRunToStartMasterAction(int run_id);

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

protected:
    std::vector<G4ThreeVector> fTranslations;
    std::vector<G4RotationMatrix> fRotations;
    std::string fVolumeName;

};

#endif // GateMotionVolumeActor_h
