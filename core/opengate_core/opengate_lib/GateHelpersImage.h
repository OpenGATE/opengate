/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHELPERSIMAGE_H
#define OPENGATE_CORE_OPENGATEHELPERSIMAGE_H

#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GateHelpers.h"
#include "itkImage.h"

template <class ImageType>
void ImageAddValue(typename ImageType::Pointer image,
                   typename ImageType::IndexType index,
                   typename ImageType::PixelType value);

template <class ImageType>
void AttachImageToVolume(typename ImageType::Pointer image,
                         std::string volumeName,
                         G4ThreeVector image_offset = G4ThreeVector(),
                         G4RotationMatrix volume_rotation = G4RotationMatrix());

template <class ImageType>
void GetStepVoxelPosition(G4Step *step, std::string hitType,
                          typename ImageType::Pointer cpp_image,
                          G4ThreeVector &position, bool &isInside,
                          typename ImageType::IndexType &index);

#include "GateHelpersImage.txx"

#endif // OPENGATE_CORE_OPENGATEHELPERSIMAGE_H
