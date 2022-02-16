/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHelpersGeometry_h
#define GamHelpersGeometry_h

#include "G4PhysicalVolumeStore.hh"
#include "G4LogicalVolumeStore.hh"
#include "GamHelpers.h"

void ComputeTransformationFromVolumeToWorld(std::string phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation);

void ComputeTransformationFromWorldToVolume(std::string phys_volume_name,
                                            G4ThreeVector &translation,
                                            G4RotationMatrix &rotation);

void ComputeTransformationFromVolumeToVolume(std::string top_phys_volume_name,
                                             std::string bottom_phys_volume_name,
                                             G4ThreeVector &translation,
                                             G4RotationMatrix &rotation);

#endif // GamHelpersGeometry_h

