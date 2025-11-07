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
  fIntersectionFlag = false;
  fNormalFlag = false;
  fNormalAngleTolerance = 0;
  fMinDistanceNormalAngleTolerance = 0;
  fDistanceDependentAngleToleranceFlag = false;
  fAngle1 = 0;
  fAngle2 = 0;
  fDistance1 = 0;
  fDistance2 = 0;

  // Retrieve the solid
  const auto lvs = G4LogicalVolumeStore::GetInstance();
  const auto lv = lvs->GetVolume(fAcceptanceAngleVolumeName);
  if (!lv) {
    Fatal("Could not find logical volume named: " + fAcceptanceAngleVolumeName);
  }
  fAASolid = lv->GetSolid();

  // Init a navigator that will be used to find the transform
  const auto pvs = G4PhysicalVolumeStore::GetInstance();
  const auto world = pvs->GetVolume("world");
  fAANavigator = new G4Navigator();
  fAANavigator->SetWorldVolume(world);

  // parameters
  fIntersectionFlag = StrToBool(param.at("intersection_flag"));
  fNormalFlag = StrToBool(param.at("normal_flag"));
  fNormalAngleTolerance = StrToDouble(param.at("normal_tolerance"));
  fMinDistanceNormalAngleTolerance =
      StrToDouble(param.at("normal_tolerance_min_distance"));
  fNormalVector = StrToG4ThreeVector(param.at("normal_vector"));

  if (fNormalAngleTolerance <= 0) {
    Fatal("Normal angle tolerance must be strictly positive while it is " +
          std::to_string(fNormalAngleTolerance));
  }

  // DistDep -> not recommended (too slow), prefer normal_tolerance_min_distance
  fDistanceDependentAngleToleranceFlag =
      StrToBool(param.at("distance_dependent_normal_tolerance"));
  fAngle1 = StrToDouble(param.at("angle1"));
  fAngle2 = StrToDouble(param.at("angle2"));
  fDistance1 = StrToDouble(param.at("distance1"));
  fDistance2 = StrToDouble(param.at("distance2"));
  if (fDistance1 >= fDistance2) {
    Fatal(
        "For 'distance_dependent_normal_tolerance', Distance1 must be strictly "
        "less than distance2 " +
        std::to_string(fDistance1) + " " + std::to_string(fDistance2));
  }
  a = (1.0 / tan(fAngle1) - 1.0 / tan(fAngle2)) / (fDistance1 - fDistance2);
  b = 1.0 / tan(fAngle2) - a * fDistance2;
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
  if (fIntersectionFlag) {
    const auto localPosition = fAATransform.TransformPoint(position);
    dist = fAASolid->DistanceToIn(localPosition, localDirection);
    if (dist == kInfinity)
      return false;
  }
  if (fNormalFlag) {
    if (dist < fMinDistanceNormalAngleTolerance)
      return true;
    const auto angle = fNormalVector.angle(localDirection);
    return angle < fNormalAngleTolerance;
  }
  return true;
}

bool GateAcceptanceAngleSingleVolume::DistanceDependentToleranceTest(
    // This is very slow, (3x than other methods)
    // We recommend not using this method
    const double angle, const double dist) const {
  const double tol = atan(1.0 / (a * dist + b));

  if (tol < 0)
    return true;
  return angle < tol;
}
