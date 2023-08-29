/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAcceptanceAngleTester.h"
#include "G4LogicalVolumeStore.hh"
#include "G4Navigator.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

GateAcceptanceAngleTester::GateAcceptanceAngleTester(
    std::string volume, std::map<std::string, std::string> &param) {
  fAcceptanceAngleVolumeName = volume;
  fAASolid = nullptr;
  fAANavigator = nullptr;

  // Retrieve the solid
  auto lvs = G4LogicalVolumeStore::GetInstance();
  auto lv = lvs->GetVolume(fAcceptanceAngleVolumeName);
  fAASolid = lv->GetSolid();

  // Init a navigator that will be used to find the transform
  auto pvs = G4PhysicalVolumeStore::GetInstance();
  auto world = pvs->GetVolume("world");
  fAANavigator = new G4Navigator();
  fAANavigator->SetWorldVolume(world);

  // parameters
  fIntersectionFlag = StrToBool(param["intersection_flag"]);
  fNormalFlag = StrToBool(param["normal_flag"]);
  fNormalAngleTolerance = StrToDouble(param["normal_tolerance"]);
  fNormalVector = StrToG4ThreeVector(param["normal_vector"]);
}

GateAcceptanceAngleTester::~GateAcceptanceAngleTester() { delete fAARotation; }

void GateAcceptanceAngleTester::UpdateTransform() {
  // Get the transformation
  G4ThreeVector tr;
  fAARotation = new G4RotationMatrix; // FIXME to delete each run ?
  ComputeTransformationFromWorldToVolume(fAcceptanceAngleVolumeName, tr,
                                         *fAARotation);
  // It is not fully clear why the AffineTransform need the inverse
  fAATransform = G4AffineTransform(fAARotation->inverse(), tr);
}

bool GateAcceptanceAngleTester::TestIfAccept(
    const G4ThreeVector &position, const G4ThreeVector &momentum_direction) {
  auto localPosition = fAATransform.TransformPoint(position);
  auto localDirection = (*fAARotation) * (momentum_direction);
  if (fIntersectionFlag) {
    auto dist = fAASolid->DistanceToIn(localPosition, localDirection);
    if (dist == kInfinity)
      return false;
  }
  if (fNormalFlag) {
    auto angle = fNormalVector.angle(localDirection);
    if (angle > fNormalAngleTolerance)
      return false;
  }
  return true;
}
