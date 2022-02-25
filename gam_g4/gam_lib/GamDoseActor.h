/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamDoseActor_h
#define GamDoseActor_h

#include <pybind11/stl.h>
#include "G4VPrimitiveScorer.hh"
#include "GamVActor.h"
#include "itkImage.h"

namespace py = pybind11;

class GamDoseActor : public GamVActor {

public:

    // Constructor
    GamDoseActor(py::dict &user_info);

    virtual void ActorInitialize();

    // Main function called every step in attached volume
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    virtual void EndSimulationAction();

    // Image type is 3D float by default
    typedef itk::Image<float, 3> ImageType;

    // The image is accessible on py side (shared by all threads)
    ImageType::Pointer cpp_edep_image;

    // Option: indicate if we must compute uncertainty
    bool fUncertaintyFlag;

    // For uncertainty computation, we need temporary images
    ImageType::Pointer cpp_square_image;
    ImageType::Pointer cpp_temp_image;
    ImageType::Pointer cpp_last_id_image;

    std::string fPhysicalVolumeName;

    G4ThreeVector fInitialTranslation;

};

#endif // GamDoseActor_h
