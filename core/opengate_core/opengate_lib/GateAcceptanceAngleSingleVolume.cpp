/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAcceptanceAngleSingleVolume.h"
#include "G4LogicalVolumeStore.hh"
#include "G4Navigator.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

GateAcceptanceAngleSingleVolume::GateAcceptanceAngleSingleVolume(
    const std::string &volume,
    const std::map<std::string, std::string> &param) {
  fAcceptanceAngleVolumeName = volume;
  fAASolid = nullptr;
  fAANavigator = nullptr;
  fAARotation = nullptr;
  fEnableIntersectionCheck = false;
  fEnableAngleCheck = false;
  fAngleToleranceMax = 0;
  fAngleCheckProximityDistance = 0;

  // Retrieve the solid
  const auto lvs = G4LogicalVolumeStore::GetInstance();
  const auto lv = lvs->GetVolume(fAcceptanceAngleVolumeName);
  if (!lv) {
    Fatal("Could not find logical volume named: " + fAcceptanceAngleVolumeName);
    exit(0);
  }
  fAASolid = lv->GetSolid();

  // Init a navigator that will be used to find the transform
  const auto pvs = G4PhysicalVolumeStore::GetInstance();
  const auto world = pvs->GetVolume("world");
  fAANavigator = new G4Navigator();
  fAANavigator->SetWorldVolume(world);

  // parameters
  fEnableIntersectionCheck =
      StrToBool(ParamAt(param, "enable_intersection_check"));
  fEnableAngleCheck = StrToBool(ParamAt(param, "enable_angle_check"));
  fAngleCheckProximityDistance =
      StrToDouble(ParamAt(param, "angle_check_proximity_distance"));
  fAngleReferenceVector =
      StrToG4ThreeVector(ParamAt(param, "angle_check_reference_vector"));
  fAngleToleranceMax = StrToDouble(ParamAt(param, "angle_tolerance_max"));
  fAngleToleranceMin = StrToDouble(ParamAt(param, "angle_tolerance_min"));
  fAngleToleranceProximal =
      StrToDouble(ParamAt(param, "angle_tolerance_proximal"));

  // Validation
  if (fAngleToleranceMin < 0.0) {
    DDD(fAngleToleranceMin);
    Fatal("angle_tolerance_min cannot be negative.");
  }
  if (fAngleToleranceMin >= fAngleToleranceMax) {
    DDD(fAngleToleranceMin);
    DDD(fAngleToleranceMax);
    Fatal("angle_tolerance_min must be less than angle_tolerance_max");
  }
}

GateAcceptanceAngleSingleVolume::~GateAcceptanceAngleSingleVolume() {
  delete fAARotation;
  delete fAANavigator;
}

void GateAcceptanceAngleSingleVolume::UpdateTransform() {

  if (fAARotation == nullptr)
    fAARotation = new G4RotationMatrix;

  // Get the transformation
  G4ThreeVector tr;
  ComputeTransformationFromWorldToVolume(fAcceptanceAngleVolumeName, tr,
                                         *fAARotation, true);
  // It is not fully clear why the AffineTransform need the inverse
  fAATransform = G4AffineTransform(fAARotation->inverse(), tr);
}

bool GateAcceptanceAngleSingleVolume::TestIfAccept(
    const G4ThreeVector &position,
    const G4ThreeVector &momentum_direction) const {
  const auto localDirection = (*fAARotation) * (momentum_direction);
  double dist = 0;
  if (fEnableIntersectionCheck) {
    const auto localPosition = fAATransform.TransformPoint(position);
    dist = fAASolid->DistanceToIn(localPosition, localDirection);
    if (dist == kInfinity)
      return false;
  }
  if (fEnableAngleCheck) {
    const auto angle = fAngleReferenceVector.angle(localDirection);
    if (dist < fAngleCheckProximityDistance) {
      return angle < fAngleToleranceProximal;
    }
    return (angle < fAngleToleranceMax) && (angle >= fAngleToleranceMin);
  }
  return true;
}
