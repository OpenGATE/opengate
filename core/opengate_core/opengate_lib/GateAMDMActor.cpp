/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   LGPL, see LICENSE.md.
   Original AMDM implementation: Hermann Fuchs, April 2025.
   -------------------------------------------------- */
#include "GateAMDMActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersGeometry.h"
#include "GateHelpersImage.h"
#include <G4RandomTools.hh>
#include <cmath>
#include <limits>
#include <stdexcept>

GateAMDMActor::GateAMDMActor(py::dict &user_info)
    : GateVActor(user_info, true) {}

void GateAMDMActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fBins = DictGetInt(user_info, "AMDM_Bins");
  fHitType = DictGetStr(user_info, "hit_type");
  if (fHitType != "random" && fHitType != "pre" && fHitType != "post" &&
      fHitType != "middle")
    throw std::invalid_argument(
        "AMDM hit_type must be random, pre, post or middle");
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fRotation = DictGetG4RotationMatrix(user_info, "rotation");
  fTable.Read(DictGetStr(user_info, "LUTfilename"), fBins);
}

void GateAMDMActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  cpp_amdm_restricted_edep_image = ImageType::New();
  cpp_amdm_delta_image = ImageType4D::New();
  cpp_amdm_gamma_image = ImageType4D::New();
}

void GateAMDMActor::BeginOfRunActionMasterThread(int) {
  NbOfEvent = 0;
  // Python supplies fresh zero-filled raw buffers for each run. Only attach the
  // 3D domain: the generic attachment helper initializes only three axes.
  G4ThreeVector volumeTranslation;
  G4RotationMatrix volumeRotation;
  ComputeTransformationFromVolumeToWorld(fPhysicalVolumeName, volumeTranslation,
                                         volumeRotation, true);
  G4ThreeVector center;
  const auto size =
      cpp_amdm_restricted_edep_image->GetLargestPossibleRegion().GetSize();
  const auto spacing = cpp_amdm_restricted_edep_image->GetSpacing();
  for (unsigned int i = 0; i < 3; ++i)
    center[i] = -(size[i] - 1.0) * spacing[i] / 2.0;
  const auto spatialOrigin =
      volumeTranslation + volumeRotation * (fRotation * center + fTranslation);
  const auto spatialRotation = volumeRotation * fRotation;
  ImageType::PointType origin3;
  ImageType::DirectionType direction3;
  for (unsigned int i = 0; i < 3; ++i) {
    origin3[i] = spatialOrigin[i];
    for (unsigned int j = 0; j < 3; ++j)
      direction3[i][j] = spatialRotation(i, j);
  }
  cpp_amdm_restricted_edep_image->SetOrigin(origin3);
  cpp_amdm_restricted_edep_image->SetDirection(direction3);
  ImageType4D::PointType origin;
  ImageType4D::DirectionType direction;
  direction.SetIdentity();
  origin.Fill(0);
  for (unsigned int i = 0; i < 3; ++i) {
    origin[i] = cpp_amdm_restricted_edep_image->GetOrigin()[i];
    for (unsigned int j = 0; j < 3; ++j)
      direction[i][j] = cpp_amdm_restricted_edep_image->GetDirection()[i][j];
  }
  for (auto image : {cpp_amdm_delta_image, cpp_amdm_gamma_image}) {
    image->SetOrigin(origin);
    image->SetDirection(direction);
  }
}

void GateAMDMActor::BeginOfEventAction(const G4Event *) {
  std::lock_guard<std::mutex> lock(fScoringMutex);
  ++NbOfEvent;
}

std::vector<double> GateAMDMActor::Lookup(int charge, double energy) const {
  std::vector<double> values;
  fTable.Find(charge, energy, values);
  return values; // empty means this charge/sample does not contribute
}

void GateAMDMActor::SteppingAction(G4Step *step) {
  const auto pre = step->GetPreStepPoint()->GetPosition();
  const auto post = step->GetPostStepPoint()->GetPosition();
  auto position = post;
  if (fHitType == "pre")
    position = pre;
  else if (fHitType == "middle")
    position = pre + 0.5 * (post - pre);
  else if (fHitType == "random")
    position = pre + G4UniformRand() * (post - pre);
  // As in DoseActor, the attached image domain is in world coordinates.
  ImageType::PointType point;
  for (unsigned int i = 0; i < 3; ++i)
    point[i] = position[i];
  ImageType::IndexType index;
  if (!cpp_amdm_restricted_edep_image->TransformPhysicalPointToIndex(point,
                                                                     index))
    return;
  const auto *track = step->GetTrack();
  const int charge = static_cast<int>(track->GetDefinition()->GetPDGCharge());
  if (charge <= 0)
    return;
  const int mass = track->GetDefinition()->GetBaryonNumber();
  const double kineticEnergy = track->GetKineticEnergy() / CLHEP::MeV;
  // Preserve legacy applicability, including its zero-baryon rule: positive
  // energy / 0 samples the upper endpoint; 0 / 0 contributes nothing.
  const double energy =
      mass == 0 ? (kineticEnergy > 0 ? std::numeric_limits<double>::infinity()
                                     : std::numeric_limits<double>::quiet_NaN())
                : kineticEnergy / mass;
  auto values = Lookup(charge, energy);
  if (values.empty())
    return;
  const double edep =
      step->GetTotalEnergyDeposit() / CLHEP::MeV * track->GetWeight();
  ImageType4D::IndexType index4;
  for (unsigned int i = 0; i < 3; ++i)
    index4[i] = index[i];
  // One actor-owned lock protects all shared accumulator updates.
  std::lock_guard<std::mutex> lock(fScoringMutex);
  ImageAddValue<ImageType>(cpp_amdm_restricted_edep_image, index, edep);
  for (int b = 0; b < fBins; ++b) {
    index4[3] = b;
    const double delta = values[fBins + b] * edep;
    ImageAddValue<ImageType4D>(cpp_amdm_delta_image, index4, delta);
    ImageAddValue<ImageType4D>(cpp_amdm_gamma_image, index4, values[b] * delta);
  }
}
