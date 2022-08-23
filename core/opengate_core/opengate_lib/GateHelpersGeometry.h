/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHELPERSGEOMETRY_H
#define OPENGATE_CORE_OPENGATEHELPERSGEOMETRY_H

#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GateHelpers.h"

void ComputeTransformationFromVolumeToWorld(std::string phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation);

void ComputeTransformationFromWorldToVolume(std::string phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation);

#endif // OPENGATE_CORE_OPENGATEHELPERSGEOMETRY_H
