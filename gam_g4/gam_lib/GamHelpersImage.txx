/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4LogicalVolume.hh"
#include "GamHelpersGeometry.h"

template<class ImageType>
void ImageAddValue(typename ImageType::Pointer image,
                   typename ImageType::IndexType index,
                   typename ImageType::PixelType value) {
    auto v = image->GetPixel(index); // FIXME maybe 2 x FastComputeOffset can be spared
    image->SetPixel(index, v + value);
}

template<class ImageType>
void AttachImageToVolume(typename ImageType::Pointer image,
                         std::string volumeName,
                         G4ThreeVector initial_translation) {
    // get image center
    auto size = image->GetLargestPossibleRegion().GetSize();
    auto spacing = image->GetSpacing();
    G4ThreeVector center;
    for (auto i = 0; i < 3; i++)
        center[i] = size[i] * spacing[i] / 2.0;

    // get transformation from world to volume
    G4ThreeVector translation;
    G4RotationMatrix rotation;
    ComputeTransformationFromVolumeToWorld(volumeName, translation, rotation);

    // compute origin and direction
    // (need to convert from itk::PointType to G4ThreeVector)
    G4ThreeVector center_global = rotation * center + translation;
    G4ThreeVector origin;
    for (auto i = 0; i < 3; i++)
        origin[i] = size[i] * spacing[i] / -2.0 + spacing[i] / 2.0 + initial_translation[i];
    origin = rotation * origin + translation;

    // set both
    typename ImageType::PointType o;
    typename ImageType::DirectionType dir;
    for (auto i = 0; i < 3; i++) {
        o[i] = origin[i];
        for (auto j = 0; j < 3; j++)
            dir[i][j] = rotation(i, j);
    }
    image->SetOrigin(o);
    image->SetDirection(dir);
}

