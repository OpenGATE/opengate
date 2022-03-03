/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVSource_h
#define GamVSource_h

#include <pybind11/stl.h>
#include "G4Event.hh"
#include "G4RotationMatrix.hh"

namespace py = pybind11;

class GamVSource {

public:

    GamVSource();

    virtual ~GamVSource();

    // May be used to clear some allocated data during a thread
    // (see for example GamGenericSource)
    virtual void CleanWorkerThread() {}

    // Called at initialisation to set the source properties from a single dict
    virtual void InitializeUserInfo(py::dict &user_info);

    virtual void PrepareNextRun();

    virtual double PrepareNextTime(double current_simulation_time);

    virtual void GeneratePrimaries(G4Event *event, double time);

    virtual void SetOrientationAccordingToMotherVolume();

    virtual void ComputeTransformationAccordingToMotherVolume();

    std::string fName;
    double fStartTime;
    double fEndTime;
    std::string fMother;
    std::vector<G4ThreeVector> fTranslations;
    std::vector<G4RotationMatrix> fRotations;

    G4ThreeVector fLocalTranslation;
    G4RotationMatrix fLocalRotation;

    G4ThreeVector fGlobalTranslation;
    G4RotationMatrix fGlobalRotation;

};

#endif // GamVSource_h
