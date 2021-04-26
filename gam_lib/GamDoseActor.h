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

    // Main function called every step in attached volume
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    virtual void EndSimulationAction();

    // Image type is 3D float by default
    typedef itk::Image<float, 3> ImageType;

    // The image is accessible on py side (shared by all threads)
    ImageType::Pointer cpp_image;

};

#endif // GamDoseActor_h
