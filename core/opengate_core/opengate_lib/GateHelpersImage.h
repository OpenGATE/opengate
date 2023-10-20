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
                         G4ThreeVector initial_translation = G4ThreeVector(),
                         G4RotationMatrix img_rotation = G4RotationMatrix());

#include "GateHelpersImage.txx"

#endif // OPENGATE_CORE_OPENGATEHELPERSIMAGE_H
