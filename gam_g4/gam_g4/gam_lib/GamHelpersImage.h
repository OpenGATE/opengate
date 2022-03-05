/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GAM_G4_GAMHELPERSIMAGE_H
#define GAM_G4_GAMHELPERSIMAGE_H

#include "G4PhysicalVolumeStore.hh"
#include "G4LogicalVolumeStore.hh"
#include "GamHelpers.h"
#include "itkImage.h"

template<class ImageType>
void ImageAddValue(typename ImageType::Pointer image,
                   typename ImageType::IndexType index,
                   typename ImageType::PixelType value);

template<class ImageType>
void AttachImageToVolume(typename ImageType::Pointer image,
                         std::string volumeName,
                         G4ThreeVector initial_translation = G4ThreeVector());

class GamVolumeVoxelizer {
public:

    GamVolumeVoxelizer();

    typedef itk::Image<unsigned char, 3> ImageType;
    typename ImageType::Pointer fImage;
    std::map<std::string, unsigned char> fLabels;

    void Voxelize(std::string vol_name);

};

#include "GamHelpersImage.txx"

#endif // GAM_G4_GAMHELPERSIMAGE_H

