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
  DDD("AttachImageToVolume");
  DDD(volumeName);
  //DDD(depth_axis);
  // get image center
  auto size = image->GetLargestPossibleRegion().GetSize();
  auto spacing = image->GetSpacing();
  //G4ThreeVector center;
  //for (auto i = 0; i < 3; i++)
  //  center[i] = size[i] * spacing[i] / 2.0;
  DDD(size);
  DDD(spacing);

  // get transformation
  G4ThreeVector translation;
  G4RotationMatrix rotation;
  ComputeTransformationFromVolumeToWorld(volumeName, translation, rotation);
  DDD(translation);
  //DDD(rotation);
  //ComputeTransformationFromWorldToVolume(volumeName, translation, rotation);
  DDD(translation);
  DDD(rotation);
  DDD(image_offset);

  // img rotation ?
  G4RotationMatrix A;
  DDD(volume_rotation);
  A.set(0, 90*CLHEP::degree, 0);
  G4ThreeVector axis(0, 1, 0); // FIXME
  double angle = 0;
  if (true) {
    angle = 90 * CLHEP::degree;
    A.set(axis, angle);

    G4RotationMatrix volume_rotation2;
    //volume_rotation.set(0, 90*CLHEP::degree, 0);
    G4ThreeVector axis2(1, 0, 0); // FIXME
    volume_rotation2.set(axis2, 90 * CLHEP::degree);
    A = volume_rotation2 * A;
    DDD(A);
  }
  //volume_rotation.set(axis, angle);

  // img rotation is to rotate the image according to the orientation of the volume
  // For example, in a crystal, the depth could be Z, or X or Y dimension, while the image is always with depth=Z

  DDD(volume_rotation);
  //auto rot = volume_rotation * rotation;
  auto rot = rotation * volume_rotation;
  //rotation = volume_rotation*rotation;
  DDD(rot);

  auto tr = volume_rotation * translation;
  DDD(tr);

  image_offset = volume_rotation * image_offset;
  DDD(image_offset);

  // compute origin and direction
  // (need to convert from itk::PointType to G4ThreeVector)
  //G4ThreeVector center_global = rotation * center + translation;
  //DDD(center_global);
  G4ThreeVector origin;
  for (auto i = 0; i < 3; i++)
    origin[i] = size[i] * spacing[i] / -2.0 + spacing[i] / 2.0 + image_offset[i];
  DDD(origin);
  //origin = rotation * origin + translation;
  //origin = rotation * origin + translation + image_offset;//translation;
  //origin = rotation * origin + translation + image_offset;//translation;
  origin = rot * origin + translation;//+ image_offset;//translation;
  //DDD(origin);
  //origin = volume_rotation * origin;
  //origin = rotation * origin + tr;
  DDD(origin);

  // set both (itk data structure)
  typename ImageType::PointType o;
  typename ImageType::DirectionType dir;
  for (auto i = 0; i < 3; i++) {
    o[i] = origin[i];
    for (auto j = 0; j < 3; j++)
      dir[i][j] = rot(i, j);
    //dir[i][j] = rotation(i, j);
  }
  image->SetOrigin(o);
  image->SetDirection(dir);
}
