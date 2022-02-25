/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamImageNestedParameterisation_h
#define GamImageNestedParameterisation_h

#include "GamHelpers.h"
#include "G4VNestedParameterisation.hh"
#include "G4NistManager.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VTouchable.hh"
#include "itkImage.h"

class GamImageNestedParameterisation : public G4VNestedParameterisation {

public:

    // Slice position in mm
    std::vector<G4double> fpZ;
    // List of pixel value <-> material
    std::vector<G4Material *> fMaterials;
    // The image, float for the moment. Short later.
    typedef itk::Image<float, 3> ImageType;
    ImageType::Pointer cpp_image;

    GamImageNestedParameterisation();

    void initialize_image();

    void initialize_material(std::vector<std::string> materials);

    virtual G4Material *ComputeMaterial(G4VPhysicalVolume * /*currentVol*/,
                                        const G4int repNo,
                                        const G4VTouchable *parentTouch = nullptr);

    virtual G4int GetNumberOfMaterials() const;

    virtual G4Material *GetMaterial(G4int idx) const;

    virtual void ComputeTransformation(const G4int no,
                                       G4VPhysicalVolume *currentPV) const;

};

#endif // GamImageNestedParameterisation_h
