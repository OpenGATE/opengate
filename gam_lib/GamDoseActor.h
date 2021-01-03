/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamDoseActor_h
#define GamDoseActor_h

#include "G4VPrimitiveScorer.hh"
#include "GamVActor.h"
#include "itkImage.h"

class GamDoseActor : public GamVActor {

public:

    GamDoseActor();

    //virtual void BeforeStart();

    // Main function called every step in attached volume
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    // Debug, will be removed
    void SaveImage();

    // Image type is 3D float by default
    typedef itk::Image<float, 3> ImageType;

    // The image is accessible on py side
    ImageType::Pointer cpp_image;

protected:
    ImageType::IndexType index;
    ImageType::PointType point;

};

#endif // GamDoseActor_h
