/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamImageHelpers_h
#define GamImageHelpers_h

#include "G4PhysicalVolumeStore.hh"
#include "GamHelpers.h"

template<class ImageType>
void ImageAddValue(typename ImageType::Pointer image,
                   typename ImageType::IndexType index,
                   typename ImageType::PixelType value);

template<class ImageType>
void AttachImageToVolume(typename ImageType::Pointer image,
                         std::string volumeName,
                         G4ThreeVector initial_translation=G4ThreeVector());

void ComputeTransformationFromWorldToVolume(std::string volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation);

#include "GamImageHelpers.txx"

#endif // GamImageHelpers_h

