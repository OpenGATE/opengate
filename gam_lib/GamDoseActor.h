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

    virtual void EndSimulationAction();

    // Image type is 3D float by default
    typedef itk::Image<float, 3> ImageType;

    // The image is accessible on py side (shared by all threads)
    ImageType::Pointer cpp_edep_image;
    ImageType::Pointer cpp_uncertainty_image;

    // for uncertainty
    ImageType::Pointer cpp_square_image;
    ImageType::Pointer cpp_temp_image;
    ImageType::Pointer cpp_last_id_image;

    bool fUncertaintyFlag;

};

#endif // GamDoseActor_h
