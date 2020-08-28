/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamDoseActor3_h
#define GamDoseActor3_h

#include "G4VPrimitiveScorer.hh"
#include "GamVActor.h"
#include "itkImage.h"

class GamDoseActor3 : public GamVActor {

public:

    GamDoseActor3();

    virtual void BeforeStart();

    virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    typedef itk::Image<float, 3> ImageType;
    ImageType::Pointer cpp_image;

protected:
    ImageType::IndexType index;
    ImageType::PointType point;

};

#endif // GamDoseActor3_h
