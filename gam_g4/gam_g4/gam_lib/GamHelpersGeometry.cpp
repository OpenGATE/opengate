/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHelpersImage.h"

void ComputeTransformationFromVolumeToWorld(std::string phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation) {
    translation = {0, 0, 0};
    rotation = G4RotationMatrix::IDENTITY;
    std::string name = phys_volume_name;
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    while (name != "world") {
        auto phys = pvs->GetVolume(name);
        auto tr = phys->GetObjectTranslation();
        auto rot = *phys->GetObjectRotation();
        rotation = rot * rotation;
        translation = rot * translation + tr;
        name = phys->GetMotherLogical()->GetName();
    }
}

void ComputeTransformationFromWorldToVolume(std::string phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation) {
    ComputeTransformationFromVolumeToWorld(phys_volume_name, translation, rotation);
    // Transfo is R(x) + t = y
    // We look for R'(y) + t' = x
    // R' = R-1 and t' = R'(-t)
    rotation.invert();
    translation = rotation * translation;
    translation = -translation;
}