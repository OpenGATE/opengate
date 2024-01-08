/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpersImage.h"

void ComputeTransformationFromVolumeToWorld(const std::string &phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation,
                                            bool initialize) {
  if (initialize) {
    translation = {0, 0, 0};
    rotation = G4RotationMatrix::IDENTITY;
  }
  std::string name = phys_volume_name;
  auto pvs = G4PhysicalVolumeStore::GetInstance();
  while (name != "world") {
    auto phys = pvs->GetVolume(name);
    auto tr = phys->GetObjectTranslation();
    // auto rot = *phys->GetObjectRotation();
    auto rot = phys->GetObjectRotationValue();
    rotation = rot * rotation;
    translation = rot * translation + tr;
    // Warning, the world can be a parallel world
    if (phys->GetMotherLogical() == nullptr)
      name = "world";
    else
      name = phys->GetMotherLogical()->GetName();
  }
}

void ComputeTransformationFromWorldToVolume(const std::string &phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation,
                                            bool initialize) {
  ComputeTransformationFromVolumeToWorld(phys_volume_name, translation,
                                         rotation, initialize);
  // Transformation is R(x) + t = y
  // We look for R'(y) + t' = x
  // R' = R-1 and t' = R'(-t)
  // auto rot_inv = rotation.inverse();
  rotation.invert();
  translation = rotation * translation;
  translation = -translation;
}
