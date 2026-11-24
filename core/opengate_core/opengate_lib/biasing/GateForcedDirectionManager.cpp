/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateForcedDirectionManager.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersGeometry.h"
#include <G4LogicalVolumeStore.hh>
#include <G4Run.hh>
#include <G4RunManager.hh>

GateForcedDirectionManager::GateForcedDirectionManager() {
  fEnabledFlag = false;
  fFDLastRunId = -1;
  fFDRotation = nullptr;
  fSinThetaMax = 0;
  fWeight = 1.0;
  fSolid = nullptr;
  fCosThetaMax = 0;
  fAngleToleranceMax = 0;
  fAngleToleranceMin = 0;
  fEnableIntersectionCheck = false;
  fSinThetaMin = 0;
  fCosThetaMin = 0;
  fLogSamplingFlag = false;
  fU0 = 0;
  fUMin = 0;
  fLogRange = 0;
}

GateForcedDirectionManager::~GateForcedDirectionManager() = default;

void GateForcedDirectionManager::Initialize(
    const std::map<std::string, std::string> &user_info,
    const bool is_valid_type) {
  // Main flag
  const auto s = ParamAt(user_info, "policy");
  fEnabledFlag = s == "ForceDirection" && is_valid_type;
  if (!fEnabledFlag)
    return;

  // Check if we test the intersection with the volumes
  fEnableIntersectionCheck =
      StrToBool(ParamAt(user_info, "enable_intersection_check"));
  // const bool b3 = StrToBool(ParamAt(user_info, "enable_angle_check"));

  // Volumes
  fAcceptanceAngleVolumeNames =
      GetVectorFromMapString(user_info, "target_volumes");
  fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();

  // (we cannot use py::dict here as it is lost at the end of the function)
  // fAcceptanceAngleParam = DictToMap(user_info);
  if (fAcceptanceAngleVolumeNames.size() > 1) {
    Fatal("Cannot use several volume for forced direction flag");
  }

  if (!fEnabledFlag)
    return;

  fAngleReferenceVector =
      StrToG4ThreeVector(ParamAt(user_info, "angle_check_reference_vector"));
  fAngleToleranceMax = StrToDouble(ParamAt(user_info, "angle_tolerance_max"));
  fAngleToleranceMin = StrToDouble(ParamAt(user_info, "angle_tolerance_min"));

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

  // Precompute values
  fSinThetaMin = std::sin(fAngleToleranceMin);
  fCosThetaMin = std::cos(fAngleToleranceMin);
  fSinThetaMax = std::sin(fAngleToleranceMax);
  fCosThetaMax = std::cos(fAngleToleranceMax);

  // Sampling of the direction in the cone
  // (missing in the user info of older simulations: uniform)
  std::string sampling = "uniform";
  if (user_info.count("angle_sampling") > 0)
    sampling = ParamAt(user_info, "angle_sampling");
  if (sampling != "uniform" && sampling != "log") {
    Fatal("angle_sampling must be 'uniform' or 'log', not '" + sampling + "'");
  }
  fLogSamplingFlag = sampling == "log";
  if (fLogSamplingFlag) {
    const double scale =
        StrToDouble(ParamAt(user_info, "angle_sampling_scale"));
    if (scale <= 0) {
      Fatal("angle_sampling_scale must be positive with angle_sampling 'log'");
    }
    // u = 1 - cos(theta) in [fUMin, uMax], pdf q(u) = 1 / ((u + u0) L)
    fU0 = 1.0 - std::cos(scale);
    fUMin = 1.0 - fCosThetaMin;
    const double uMax = 1.0 - fCosThetaMax;
    fLogRange = std::log((uMax + fU0) / (fUMin + fU0));
  }
}

void GateForcedDirectionManager::InitializeForcedDirection() {
  if (!fEnabledFlag)
    return;
  // Retrieve the solid
  const auto lvs = G4LogicalVolumeStore::GetInstance();
  // (only one volume is possible)
  const auto lv = lvs->GetVolume(fAcceptanceAngleVolumeNames[0]);
  fSolid = lv->GetSolid();

  // update transformation
  G4ThreeVector tr;
  if (fFDRotation == nullptr)
    fFDRotation = new G4RotationMatrix;
  ComputeTransformationFromWorldToVolume(fAcceptanceAngleVolumeNames[0], tr,
                                         *fFDRotation, true);
  fAARotationInverse = fFDRotation->inverse();
  fFDTransformWorldToVolume = G4AffineTransform(fAARotationInverse, tr);

  // store the ID of this Run
  fFDLastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();

  // Generate orthogonal unit vectors to the normal
  if (std::abs(fAngleReferenceVector.x()) >
      std::abs(fAngleReferenceVector.y())) {
    fU1 =
        G4ThreeVector(fAngleReferenceVector.z(), 0, -fAngleReferenceVector.x())
            .unit();
  } else {
    fU1 =
        G4ThreeVector(0, -fAngleReferenceVector.z(), fAngleReferenceVector.y())
            .unit();
  }
  fU2 = fAngleReferenceVector.cross(fU1).unit();

  // default weight for the angle
  // fWeight = (1.0 - fCosThetaMax) / 2.0;
  fWeight = (fCosThetaMin - fCosThetaMax) / 2.0;
  if (fWeight <= 0) {
    Fatal("Invalid angle range. Check min/max normal_tolerance. Weight is zero "
          "or negative.");
  }
}

G4ThreeVector
GateForcedDirectionManager::SampleDirectionWithinCone(double &theta,
                                                      double &weight) const {
  // Uniformly sample phi between 0 and 2*pi
  const double phi = G4UniformRand() * 2 * CLHEP::pi;

  double cosTheta;
  if (fLogSamplingFlag) {
    // u = 1 - cos(theta) with the pdf q(u) = 1 / ((u + u0) L) in the cone;
    // the weight is the isotropic pdf over q: 1 / (2 q(u)) = (u + u0) L / 2
    const double u =
        (fUMin + fU0) * std::exp(G4UniformRand() * fLogRange) - fU0;
    cosTheta = 1.0 - u;
    weight = (u + fU0) * fLogRange / 2.0;
  } else {
    // Uniformly sample cos(theta) between cos(theta_min) and cos(theta_max)
    cosTheta = fCosThetaMax + G4UniformRand() * (fCosThetaMin - fCosThetaMax);
    weight = fWeight;
  }
  theta = std::acos(cosTheta);

  // Calculate the direction vector
  G4ThreeVector direction =
      fAngleReferenceVector * cosTheta +
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
  double direction_weight;
  const auto direction = SampleDirectionWithinCone(theta, direction_weight);

  // Check for intersection with the detector plane
  const auto localPosition = fFDTransformWorldToVolume.TransformPoint(position);
  if (fEnableIntersectionCheck) {
    const auto dist = fSolid->DistanceToIn(localPosition, direction);
    if (dist == kInfinity) {
      // do not intersect
      zero_energy_flag = true;
      weight = 0;
      return {1, 0, 0};
    }
  }

  // Transform the direction in the global coordinate system
  const auto globalDirection = fAARotationInverse * direction;
  weight = direction_weight;
  return globalDirection;
}
