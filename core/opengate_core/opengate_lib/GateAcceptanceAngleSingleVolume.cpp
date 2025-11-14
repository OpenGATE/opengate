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
    exit(0);
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
    const auto angle = fNormalVector.angle(localDirection);
    if (dist < fMinDistanceNormalAngleTolerance) {
      static const double fMaxAngle = 90 * CLHEP::deg; // FIXME as a parameter
      return angle < fMaxAngle;
      // return true;
    }
    // const auto angle = fNormalVector.angle(localDirection);
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
