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
    const auto *phys = pvs->GetVolume(name);
    if (phys == nullptr) {
      std::ostringstream oss;
      oss << " (ComputeTransformationFromVolumeToWorld) The volume '" << name
          << "' is not found. Here is the list of volumes: ";
      auto map = pvs->GetMap();
      for (const auto &m : map) {
        oss << m.first << " ";
      }
      oss << std::endl;
      Fatal(oss.str());
    }
    auto tr = phys->GetObjectTranslation();
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

bool IsStepInVolume(const G4Step *step, const std::string &volume_name) {
  if (!step)
    return false;

  const G4StepPoint *preStepPoint = step->GetPreStepPoint();
  if (!preStepPoint)
    return false;

  const G4TouchableHandle &touchable = preStepPoint->GetTouchableHandle();
  if (!touchable)
    return false;

  // Traverse the touchable hierarchy upwards
  for (G4int depth = 0; depth < touchable->GetHistoryDepth(); ++depth) {
    const G4VPhysicalVolume *volume = touchable->GetVolume(depth);
    if (!volume)
      continue;

    if (volume->GetName() == volume_name) {
      return true;
    }
  }
  return false;
}
