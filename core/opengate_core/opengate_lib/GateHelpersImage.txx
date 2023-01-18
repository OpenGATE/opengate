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
                         int depth_axis,
                         G4ThreeVector initial_translation) {
  DDD("AttachImageToVolume");
  DDD(volumeName);
  DDD(depth_axis);
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
  DDD(initial_translation);

  // img rotation ?
  G4RotationMatrix img_rotation;
  //img_rotation.set(0, 90*CLHEP::degree, 0);
  G4ThreeVector axis(0, 1, 0); // FIXME
  double angle = 0;
  if (depth_axis == 0) {
    angle = 90 * CLHEP::degree;
    img_rotation.set(axis, angle);

    G4RotationMatrix img_rotation2;
    //img_rotation.set(0, 90*CLHEP::degree, 0);
    G4ThreeVector axis2(1, 0, 0); // FIXME
    img_rotation2.set(axis2, 90 * CLHEP::degree);
    img_rotation = img_rotation2 * img_rotation;
    DDD(img_rotation);
  }
  //img_rotation.set(axis, angle);

  // img rotation is to rotate the image according to the orientation of the volume
  // For example, in a crystal, the depth could be Z, or X or Y dimension, while the image is always with depth=Z

  DDD(img_rotation);
  //auto rot = img_rotation * rotation;
  auto rot = rotation * img_rotation;
  //rotation = img_rotation*rotation;
  DDD(rot);

  auto tr = img_rotation * translation;
  DDD(tr);

  initial_translation = img_rotation * initial_translation;
  DDD(initial_translation);

  // compute origin and direction
  // (need to convert from itk::PointType to G4ThreeVector)
  //G4ThreeVector center_global = rotation * center + translation;
  //DDD(center_global);
  G4ThreeVector origin;
  for (auto i = 0; i < 3; i++)
    origin[i] = size[i] * spacing[i] / -2.0 + spacing[i] / 2.0 + initial_translation[i];
  DDD(origin);
  //origin = rotation * origin + translation;
  //origin = rotation * origin + translation + initial_translation;//translation;
  //origin = rotation * origin + translation + initial_translation;//translation;
  origin = rot * origin + translation;//+ initial_translation;//translation;
  //DDD(origin);
  //origin = img_rotation * origin;
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
