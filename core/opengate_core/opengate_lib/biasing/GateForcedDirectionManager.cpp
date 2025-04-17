/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateForcedDirectionManager.h"
#include "../GateAcceptanceAngleSingleVolume.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersGeometry.h"
#include "G4LogicalVolumeStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4RunManager.hh"

GateForcedDirectionManager::GateForcedDirectionManager() {
  fEnabledFlag = false;
  fNotAcceptedEvents = 0;
  fAALastRunId = -1;
  fMaxNotAcceptedEvents = 10000;
  fAANavigator = nullptr;
  fAARotation = nullptr;
  fSinThetaMax = 0;
  fWeight = 1.0;
}

GateForcedDirectionManager::~GateForcedDirectionManager() {}

void GateForcedDirectionManager::Initialize(py::dict user_info,
                                            bool is_valid_type) {
  DDD("Initialize");
  DDD(is_valid_type);
  DDD(user_info);
  // Main flag
  fEnabledFlag = DictGetBool(user_info, "forced_direction_flag");
  if (!fEnabledFlag)
    return;

  // Check AA flags
  bool b2 = DictGetBool(user_info, "intersection_flag");
  bool b3 = DictGetBool(user_info, "normal_flag");
  if (b2 || b3) {
    std::ostringstream oss;
    oss << "Cannot use 'forced_direction_flag' mode with forced_direction_flag "
           "or normal_flag";
    Fatal(oss.str());
  }

  // Volumes
  fAcceptanceAngleVolumeNames = DictGetVecStr(user_info, "volumes");
  DDDV(fAcceptanceAngleVolumeNames);
  fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();

  // (we cannot use py::dict here as it is lost at the end of the function)
  fAcceptanceAngleParam = DictToMap(user_info);
  if (fAcceptanceAngleVolumeNames.size() > 1) {
    Fatal("Cannot use several volume for forced direction flag");
  }

  if (!fEnabledFlag)
    return;
  DDDV(fAcceptanceAngleVolumeNames);

  fNormalVector = StrToG4ThreeVector(fAcceptanceAngleParam.at("normal_vector"));
  fNormalAngleTolerance =
      StrToDouble(fAcceptanceAngleParam.at("normal_tolerance"));
  DDD(fNormalAngleTolerance);
  DDD(fNormalVector);
  DDD(fAALastRunId);

  fSinThetaMax = std::sin(fNormalAngleTolerance);
  DDD(fSinThetaMax);
  fCosThetaMax = std::cos(fNormalAngleTolerance);
  DDD(fCosThetaMax);
}

void GateForcedDirectionManager::InitializeForcedDirection() {
  DDD("InitializeForcedDirection");
  DDD(fEnabledFlag);
  if (!fEnabledFlag)
    return;

  // Retrieve the solid
  const auto lvs = G4LogicalVolumeStore::GetInstance();
  const auto lv =
      lvs->GetVolume(fAcceptanceAngleVolumeNames[0]); // FIXME several
  fAASolid = lv->GetSolid();
  DDD(fAcceptanceAngleVolumeNames[0]);

  // Init a navigator that will be used to find the transform
  const auto pvs = G4PhysicalVolumeStore::GetInstance();
  const auto world = pvs->GetVolume("world");

  if (fAANavigator == nullptr)
    fAANavigator = new G4Navigator();
  fAANavigator->SetWorldVolume(world);

  // if (fAARotation != nullptr)
  //   delete fAARotation;

  // update transfo
  G4ThreeVector tr;
  if (fAARotation == nullptr)
    fAARotation = new G4RotationMatrix;
  ComputeTransformationFromWorldToVolume(fAcceptanceAngleVolumeNames[0], tr,
                                         *fAARotation);
  // It is not fully clear why the AffineTransform need the inverse
  fAATransform = G4AffineTransform(fAARotation->inverse(), tr);

  fAARotationInverse = fAARotation->inverse();

  /*// Create the testers (only the first time)
  if (fAATesters.empty()) {
    for (const auto &name : fAcceptanceAngleVolumeNames) {
      auto *t =
          new GateAcceptanceAngleSingleVolume(name, fAcceptanceAngleParam);
      fAATesters.push_back(t);
    }
  }

  // Update the transform (all runs!)
  for (auto *t : fAATesters)
    t->UpdateTransform();
*/
  // store the ID of this Run
  fAALastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  // fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();
  DDD(fEnabledFlag);
  DDD(fAALastRunId);

  // Generate orthogonal unit vectors to the normal
  if (std::abs(fNormalVector.x()) > std::abs(fNormalVector.y())) {
    fU1 = G4ThreeVector(fNormalVector.z(), 0, -fNormalVector.x()).unit();
  } else {
    fU1 = G4ThreeVector(0, -fNormalVector.z(), fNormalVector.y()).unit();
  }
  fU2 = fNormalVector.cross(fU1).unit();

  fWeight = (1.0 - fCosThetaMax) / 2.0;
  DDD(fWeight);
}

unsigned long GateForcedDirectionManager::GetNumberOfNotAcceptedEvents() const {
  return fNotAcceptedEvents;
}

G4ThreeVector
GateForcedDirectionManager::SampleDirectionWithinCone(double &theta) {
  /*double phi = G4UniformRand() * 2 * M_PI;
  double u = G4UniformRand();
  theta = std::asin(std::sqrt(u) * fSinThetaMax);

  G4ThreeVector u1(1, 0, 0); // Orthogonal unit vector 1
  G4ThreeVector u2(0, 1, 0); // Orthogonal unit vector 2

  G4ThreeVector direction = normal + std::sin(theta) * std::cos(phi) * u1 +
  std::sin(theta) * std::sin(phi) * u2; direction = direction.unit();

  return direction;
   */

  // Uniformly sample phi between 0 and 2*pi
  double phi = G4UniformRand() * 2 * M_PI;

  // Uniformly sample cos(theta) between cos(0) and cos(theta_max)
  // double cosThetaMax = std::cos(fNormalAngleTolerance);
  double cosTheta = fCosThetaMax + G4UniformRand() * (1.0 - fCosThetaMax);
  theta = std::acos(cosTheta);

  // Generate orthogonal unit vectors to the normal
  /*G4ThreeVector u1, u2;
  if (std::abs(normal.x()) > std::abs(normal.y())) {
    u1 = G4ThreeVector(normal.z(), 0, -normal.x()).unit();
  } else {
    u1 = G4ThreeVector(0, -normal.z(), normal.y()).unit();
  }
  u2 = normal.cross(u1).unit();*/

  // Calculate the direction vector
  G4ThreeVector direction =
      fNormalVector * cosTheta +
      std::sin(theta) * (std::cos(phi) * fU1 + std::sin(phi) * fU2);

  return direction;
}

/*

 G4ThreeVector GateForcedDirectionManager::SampleDirectionWithinCone(const
G4ThreeVector &normal, double theta_max, double & theta) { double phi =
G4UniformRand() * 2 * M_PI; double u = G4UniformRand(); theta = acos(1 - u * (1
- cos(theta_max)));

  double sin_theta = sin(theta);
  G4ThreeVector localDirection(sin_theta * cos(phi), sin_theta * sin(phi),
cos(theta));

  // Create a rotation matrix to align the local z-axis with the normal vector
  G4ThreeVector z_axis(0, 0, 1);
  G4RotationMatrix rotation;
  rotation.rotateAxes(z_axis, normal.orthogonal(), normal); // Rotate z to
normal

  // Transform the local direction to the global frame
  G4ThreeVector direction = rotation * localDirection;

  return direction.unit();
}

 *
 */

G4ThreeVector GateForcedDirectionManager::GenerateForcedDirection(
    G4ThreeVector position, bool &zero_energy_flag, double &weight) {
  // DDD("GenerateForcedDirection");
  // DDD(position);
  if (fAALastRunId !=
      G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID())
    InitializeForcedDirection();

  // Sample direction within a cone
  double theta;
  auto direction = SampleDirectionWithinCone(theta);

  // Transform direction in the global coordinate system
  const auto globalDirection = fAARotationInverse * direction;

  // Check for intersection with the detector plane
  const auto localPosition = fAATransform.TransformPoint(position);
  auto dist = fAASolid->DistanceToIn(localPosition, direction);
  auto intersects = (dist != kInfinity);

  if (intersects) {
    // Calculate the weight for the sampled direction
    // weight = std::pow(std::sin(fNormalAngleTolerance), 2) / (4.0 *
    // std::cos(theta));

    // weight = (1.0 - fCosThetaMax) / 2.0;
    weight = fWeight;

    return globalDirection;
  } else {
    // Fallback strategy if no intersection is found
    zero_energy_flag = true;
    weight = 0;
    // DDD(zero_energy_flag);
    return G4ThreeVector(0, 0, 0); // Return a zero vector or handle accordingly
  }
}
