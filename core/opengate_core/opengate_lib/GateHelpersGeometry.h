/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHELPERSGEOMETRY_H
#define OPENGATE_CORE_OPENGATEHELPERSGEOMETRY_H

#include "G4LogicalVolumeStore.hh"
#include "GateHelpers.h"

void ComputeTransformationFromVolumeToWorld(const std::string &phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation,
                                            bool initialize = false);

void ComputeTransformationFromWorldToVolume(const std::string &phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation,
                                            bool initialize = false);

bool IsStepInVolume(const G4Step *step, const std::string &volume_name);

#endif // OPENGATE_CORE_OPENGATEHELPERSGEOMETRY_H
