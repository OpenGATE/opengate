/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamImageHelpers.h"

// gam.attach_image_to_volume(self.simulation, self.image, self.user_info.mother)
// gam.update_image_py_to_cpp(self.image, self.fImage, False)

void ComputeTransformationFromWorldToVolume(std::string volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation) {
    translation = {0, 0, 0};
    rotation = G4RotationMatrix::IDENTITY;
    std::string name = volume_name;
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