/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateForcedDirectionManager.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersGeometry.h"
#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4RunManager.hh"

GateForcedDirectionManager::GateForcedDirectionManager() {
  fEnabledFlag = false;
  fFDLastRunId = -1;
  fNavigator = nullptr;
  fFDRotation = nullptr;
  fSinThetaMax = 0;
  fWeight = 1.0;
  fSolid = nullptr;
  fCosThetaMax = 0;
  fNormalAngleTolerance = 0;
}

GateForcedDirectionManager::~GateForcedDirectionManager() {}

void GateForcedDirectionManager::Initialize(py::dict user_info,
                                            const bool is_valid_type) {
  // Main flag
  fEnabledFlag =
      DictGetBool(user_info, "forced_direction_flag") && is_valid_type;
  if (!fEnabledFlag)
    return;

  // Check AA flags
  const bool b2 = DictGetBool(user_info, "intersection_flag");
  const bool b3 = DictGetBool(user_info, "normal_flag");
  if (b2 || b3) {
    std::ostringstream oss;
    oss << "Cannot use 'forced_direction_flag' mode with forced_direction_flag "
           "or normal_flag";
    Fatal(oss.str());
  }

  // Volumes
  fAcceptanceAngleVolumeNames = DictGetVecStr(user_info, "volumes");
  fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();

  // (we cannot use py::dict here as it is lost at the end of the function)
  fAcceptanceAngleParam = DictToMap(user_info);
  if (fAcceptanceAngleVolumeNames.size() > 1) {
    Fatal("Cannot use several volume for forced direction flag");
  }

  if (!fEnabledFlag)
    return;

  fNormalVector = StrToG4ThreeVector(fAcceptanceAngleParam.at("normal_vector"));
  fNormalAngleTolerance =
      StrToDouble(fAcceptanceAngleParam.at("normal_tolerance"));

  // Precompute values
  fSinThetaMax = std::sin(fNormalAngleTolerance);
  fCosThetaMax = std::cos(fNormalAngleTolerance);
}

void GateForcedDirectionManager::InitializeForcedDirection() {
  if (!fEnabledFlag)
    return;

  // Retrieve the solid
  const auto lvs = G4LogicalVolumeStore::GetInstance();
  const auto lv =
      lvs->GetVolume(fAcceptanceAngleVolumeNames[0]); // FIXME several vol ?
  fSolid = lv->GetSolid();

  // Init a navigator that will be used to find the transform
  const auto pvs = G4PhysicalVolumeStore::GetInstance();
  const auto world = pvs->GetVolume("world");

  if (fNavigator == nullptr)
    fNavigator = new G4Navigator();
  fNavigator->SetWorldVolume(world);

  // update transformation
  G4ThreeVector tr;
  if (fFDRotation == nullptr)
    fFDRotation = new G4RotationMatrix;
  ComputeTransformationFromWorldToVolume(fAcceptanceAngleVolumeNames[0], tr,
                                         *fFDRotation, true);
  fFDTransformWorldToVolume = G4AffineTransform(fFDRotation, tr);
  fAARotationInverse = fFDRotation->inverse();

  // store the ID of this Run
  fFDLastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();

  // Generate orthogonal unit vectors to the normal
  if (std::abs(fNormalVector.x()) > std::abs(fNormalVector.y())) {
    fU1 = G4ThreeVector(fNormalVector.z(), 0, -fNormalVector.x()).unit();
  } else {
    fU1 = G4ThreeVector(0, -fNormalVector.z(), fNormalVector.y()).unit();
  }
  fU2 = fNormalVector.cross(fU1).unit();

  // default weight for the angle
  fWeight = (1.0 - fCosThetaMax) / 2.0;
}

G4ThreeVector
GateForcedDirectionManager::SampleDirectionWithinCone(double &theta) const {
  // Uniformly sample phi between 0 and 2*pi
  const double phi = G4UniformRand() * 2 * M_PI;

  // Uniformly sample cos(theta) between cos(0) and cos(theta_max)
  const double cosTheta = fCosThetaMax + G4UniformRand() * (1.0 - fCosThetaMax);
  theta = std::acos(cosTheta);

  // Calculate the direction vector
  G4ThreeVector direction =
      fNormalVector * cosTheta +
      std::sin(theta) * (std::cos(phi) * fU1 + std::sin(phi) * fU2);

  return direction;
}

G4ThreeVector GateForcedDirectionManager::GenerateForcedDirection(
    const G4ThreeVector &position, bool &zero_energy_flag, double &weight) {
  if (fFDLastRunId !=
      G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID()) {
    // every run, we must update the transformations
    InitializeForcedDirection();
  }

  // Sample direction within a cone
  double theta;
  const auto direction = SampleDirectionWithinCone(theta);

  // Check for intersection with the detector plane
  const auto localPosition = fFDTransformWorldToVolume.TransformPoint(position);
  const auto dist = fSolid->DistanceToIn(localPosition, direction);

  if (dist != kInfinity) {
    // Transform the direction in the global coordinate system
    const auto globalDirection = fAARotationInverse * direction;
    weight = fWeight;
    return globalDirection;
  }
  // Fallback strategy if no intersection is found
  zero_energy_flag = true;
  weight = 0;
  return G4ThreeVector(1, 0, 0);
}
