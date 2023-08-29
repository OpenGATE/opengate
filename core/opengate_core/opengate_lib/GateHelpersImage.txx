/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4LogicalVolume.hh"
#include "GateHelpersGeometry.h"

template<class ImageType>
void ImageAddValue(typename ImageType::Pointer image,
                   typename ImageType::IndexType index,
                   typename ImageType::PixelType value) {
  auto v = image->GetPixel(index); // FIXME maybe 2 x FastComputeOffset can be spared ?
  image->SetPixel(index, v + value);
}

template<class ImageType>
void AttachImageToVolume(typename ImageType::Pointer image,
                         std::string volumeName,
                         G4ThreeVector image_offset,
                         G4RotationMatrix volume_rotation) {
  // get image properties
  auto size = image->GetLargestPossibleRegion().GetSize();
  auto spacing = image->GetSpacing();

  // get the transformation from volume to world
  G4ThreeVector translation;
  G4RotationMatrix rotation;
  ComputeTransformationFromVolumeToWorld(volumeName, translation, rotation, true);

  // volume rotation is to rotate the image according to the orientation of the volume
  // For example, in a crystal, the depth could be Z, or X or Y dimension, while the image is always with depth=Z
  auto rot = rotation * volume_rotation;
  image_offset = volume_rotation * image_offset;

  // compute origin and direction
  // (need to convert from itk::PointType to G4ThreeVector)
  G4ThreeVector origin;
  for (auto i = 0; i < 3; i++)
    origin[i] = size[i] * spacing[i] / -2.0 + spacing[i] / 2.0 + image_offset[i];
  origin = rot * origin + translation;

  // set both (itk data structure)
  typename ImageType::PointType o;
  typename ImageType::DirectionType dir;
  for (auto i = 0; i < 3; i++) {
    o[i] = origin[i];
    for (auto j = 0; j < 3; j++)
      dir[i][j] = rot(i, j);
  }
  image->SetOrigin(o);
  image->SetDirection(dir);
}
