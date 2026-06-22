/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSingleParticleSourceWindowTurbo.h"
#include "G4Threading.hh"
#include "GateHelpersDict.h"
#include "Randomize.hh"
#include <G4Event.hh>
#include <G4PrimaryParticle.hh>
#include <G4PrimaryVertex.hh>
#include <fmt/core.h>
#include <string>

GateSingleParticleSourceWindowTurbo::GateSingleParticleSourceWindowTurbo(
    std::string mother_volume)
    : GateSingleParticleSource(mother_volume) {}

void GateSingleParticleSourceWindowTurbo::SetParameters(
    G4double a1, G4double a2, G4double b1, G4double b2, G4double plane_distance,
    G4double plane_phi) {
  fA1 = a1;
  fA2 = a2;
  fB1 = b1;
  fB2 = b2;
  fPlaneDistance = plane_distance;
  fPlanePhi = plane_phi;
  fSinPlanePhi = sin(plane_phi);
  fCosPlanePhi = cos(plane_phi);
}

G4double solid_angle_pyramid(G4double a, G4double b, G4double d) {
  return 4 * atan(a * b / (2 * d * sqrt(a * a + b * b + 4 * d * d)));
}

G4double GateSingleParticleSourceWindowTurbo::GetSolidAngle(
    const G4ThreeVector &pos) const {

  // rotate with -plane_phi
  if (pos.x() * fCosPlanePhi + pos.y() * fSinPlanePhi >= fPlaneDistance) {
    G4String error_msg = fmt::format(
        "position ({}, {}, {}) is outside the plane distance {} for source: {}",
        pos.x(), pos.y(), pos.z(), fPlaneDistance, fSourceName);
    G4Exception("GateSingleParticleSourceWindowTurbo::GetSolidAngle",
                "GetSolidAngleError", FatalException, error_msg);
  }

  G4double x0 = pos.x() * fCosPlanePhi + pos.y() * fSinPlanePhi;
  G4double y0 = -pos.x() * fSinPlanePhi + pos.y() * fCosPlanePhi;
  G4double a1_rel = fA1 - y0;
  G4double a2_rel = fA2 - y0;
  G4double b1_rel = fB1 - pos.z();
  G4double b2_rel = fB2 - pos.z();
  G4double d_rel = fPlaneDistance - x0;
  G4double sa11 = solid_angle_pyramid(2 * a1_rel, 2 * b1_rel, d_rel);
  G4double sa12 = solid_angle_pyramid(2 * a1_rel, 2 * b2_rel, d_rel);
  G4double sa21 = solid_angle_pyramid(2 * a2_rel, 2 * b1_rel, d_rel);
  G4double sa22 = solid_angle_pyramid(2 * a2_rel, 2 * b2_rel, d_rel);
  G4double sa = sa11 + sa22 - sa12 - sa21;
  return fabs(sa * 0.25);
}

void GateSingleParticleSourceWindowTurbo::ThreadFunc(
    size_t count, G4double *act_ratio_all_thread,
    G4double *max_solid_angle_thread) {

  G4ThreeVector pos;
  for (size_t i = 0; i < count; i++) {
    pos = fPositionGenerator->VGenerateOne();
    G4double solid_angle = GetSolidAngle(pos);
    if (solid_angle > *max_solid_angle_thread)
      *max_solid_angle_thread = solid_angle;
    *act_ratio_all_thread += solid_angle / 4 / M_PI;
  }
}

G4double GateSingleParticleSourceWindowTurbo::InitializeBeforeRun(
    G4double &act_ratio, G4double &max_solid_angle) {
  auto start_time = std::chrono::high_resolution_clock::now();
  G4double act_ratio_all = 0;
  fMaxSolidAngle = 0;
  const size_t sampling_count_per_thread =
      fSamplingCountInit / fThreadCountInit;
  std::vector<std::thread> threads(fThreadCountInit);
  std::vector<G4double> act_ratio_all_thread(fThreadCountInit, 0);
  std::vector<G4double> max_solid_angle_thread(fThreadCountInit, 0);
  for (G4int i = 0; i < fThreadCountInit; i++) {
    threads[i] =
        std::thread(&GateSingleParticleSourceWindowTurbo::ThreadFunc, this,
                    sampling_count_per_thread, &act_ratio_all_thread[i],
                    &max_solid_angle_thread[i]);
  }
  for (G4int i = 0; i < fThreadCountInit; i++) {
    threads[i].join();
    act_ratio_all += act_ratio_all_thread[i];
    if (max_solid_angle_thread[i] > fMaxSolidAngle)
      fMaxSolidAngle = max_solid_angle_thread[i];
  }

  act_ratio = act_ratio_all / sampling_count_per_thread / fThreadCountInit;
  max_solid_angle = fMaxSolidAngle;
  auto end_time = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
      end_time - start_time);
  return duration.count() / 1e6;
}

void GateSingleParticleSourceWindowTurbo::InitializeUserInfo(
    py::dict &user_info) {
  // TODO: make this run in master thread before each run
  // and make the worker thread get info properly before each run
  // fSourceName = source_name;
  fSamplingCountInit = DictGetInt(user_info, "init_sampling_count");
  fThreadCountInit = DictGetInt(user_info, "init_number_of_threads");
  fSkip = DictGetBool(user_info, "skip_mode");

  // fActRatio = DictGetDouble(user_info, "act_ratio");
  // fMaxSolidAngle = DictGetDouble(user_info, "max_solid_angle");
  // if (not isnan(fActRatio) && not isnan(fMaxSolidAngle) and fActRatio >= 0
  // and
  //     fActRatio <= 1 and fMaxSolidAngle >= 0 and fMaxSolidAngle <= 4 * M_PI)
  //     {
  //   return;
  // } else {
  //   fMaxSolidAngle = 0;
  //   fActRatio = 0;
  // }

  // if (not G4Threading::IsMasterThread()) {
  // TBD: should I check validity of act_ratio and max_solid_angle here or in
  // python side?
  // if (isnan(fActRatio) || isnan(fMaxSolidAngle)) {
  // G4String error_msg =
  //     "activity ratio or max solid angle not set for source: ";
  // error_msg += fSourceName;
  // G4Exception("GateSingleParticleSourceWindowTurbo::Initialize",
  //             "InitializeError", FatalException, error_msg);
  // }
  // return;
  // }

  // TODO: check paramenters in python
  // if (a1 != a1 || a2 != a2 || b1 != b1 || b2 != b2 ||
  //     plane_distance != plane_distance || plane_phi != plane_phi) {
  //   G4Exception("GateWindowTurboSource::SetActRatio", "SetActRatioError",
  //               FatalException, "Not all parameters needed points are set");
  // }

  // if (a1 >= a2 || b1 >= b2) {
  //   G4Exception("GateWindowTurboSource::SetActRatio", "SetActRatioError",
  //               FatalException, "a1 >= a2 or b1 >= b2");
  // }

  // VerifyPhiTheta(samplingCount, 0.01);
}

void GateSingleParticleSourceWindowTurbo::SetPhiTheta(
    const G4ThreeVector &pos) const {
  // compare theta with cos2, to avoid complex calculation
  //   G4double cot2theta = std::copysign(1.0, dir.z()) * dir.z() * dir.z() /
  //                        (dir.x() * dir.x() + dir.y() * dir.y());
  // relationship between angular vector and theta and phi in Geant4
  // px = -sintheta * cosphi;
  // py = -sintheta * sinphi;
  // pz = -costheta;

  G4double x0 = pos.x() * fCosPlanePhi + pos.y() * fSinPlanePhi;
  G4double y0 = -pos.x() * fSinPlanePhi + pos.y() * fCosPlanePhi;
  G4double a1_rel = fA1 - y0;
  G4double a2_rel = fA2 - y0;
  G4double b1_rel = fB1 - pos.z();
  G4double b2_rel = fB2 - pos.z();
  G4double d_rel = fPlaneDistance - x0;

  G4double aamax = std::max(a1_rel * a1_rel, a2_rel * a2_rel);
  G4double aamin = std::min(a1_rel * a1_rel, a2_rel * a2_rel);
  G4double thetamax, thetamin;

  if (a1_rel < 0 and a2_rel > 0 and b2_rel > 0)
    thetamax = M_PI - atan2(d_rel, b2_rel);
  else
    thetamax = M_PI - atan2(sqrt((b2_rel > 0 ? aamin : aamax) + d_rel * d_rel),
                            b2_rel);

  if (a1_rel < 0 and a2_rel > 0 and b1_rel < 0)
    // in this case, need to check minmum/maxmum of the hyperbola
    thetamin = M_PI - atan2(d_rel, b1_rel);
  else
    thetamin = M_PI - atan2(sqrt((b1_rel > 0 ? aamax : aamin) + d_rel * d_rel),
                            b1_rel);

  fDirectionGenerator->SetMinTheta(thetamin);
  fDirectionGenerator->SetMaxTheta(thetamax);
  G4double phimin = atan2(a1_rel, d_rel) + fPlanePhi;
  G4double phimax = atan2(a2_rel, d_rel) + fPlanePhi;

  fDirectionGenerator->SetMinPhi(phimin + M_PI);
  fDirectionGenerator->SetMaxPhi(phimax + M_PI);
}

G4bool GateSingleParticleSourceWindowTurbo::CheckPosDirValid(
    const G4ThreeVector &pos, const G4ThreeVector &dir) const {
  // compare theta with cos2, to avoid complex calculation
  //   G4double cot2theta = std::copysign(1.0, dir.z()) * dir.z() * dir.z() /
  //                        (dir.x() * dir.x() + dir.y() * dir.y());

  G4double x0 = pos.x() * fCosPlanePhi + pos.y() * fSinPlanePhi;
  G4double y0 = -pos.x() * fSinPlanePhi + pos.y() * fCosPlanePhi;
  G4double a1_rel = fA1 - y0;
  G4double a2_rel = fA2 - y0;
  G4double b1_rel = fB1 - pos.z();
  G4double b2_rel = fB2 - pos.z();
  G4double d_rel = fPlaneDistance - x0;
  G4double dir_x_rotated = dir.x() * fCosPlanePhi + dir.y() * fSinPlanePhi;
  G4double dir_y_rotated = -dir.x() * fSinPlanePhi + dir.y() * fCosPlanePhi;

  G4double intersect_b = d_rel / dir_x_rotated * dir.z() + pos.z();
  G4double intersect_a = d_rel / dir_x_rotated * dir_y_rotated + y0;
  return intersect_a <= fA2 && intersect_a >= fA1 && intersect_b <= fB2 &&
         intersect_b >= fB1;
}

void GateSingleParticleSourceWindowTurbo::GeneratePos() {
  fCurrentPos = fPositionGenerator->VGenerateOne();

  // probability of the position is valid should be proportional to the solid
  // angle
  while (true) {
    G4double solid_angle = GetSolidAngle(fCurrentPos);
    if (solid_angle > fMaxSolidAngle * 1.1) {
      G4String error_msg = "solid angle of position";
      error_msg += fmt::format(" ({}, {}, {}): {}", fCurrentPos.x(),
                               fCurrentPos.y(), fCurrentPos.z(), solid_angle);
      error_msg += " is larger than max solid angle ";
      error_msg += std::to_string(fMaxSolidAngle);
      error_msg += " for source: ";
      error_msg += fSourceName;
      error_msg += "\nyou may increase max solid angle and try again";
      G4Exception("GateWindowTurboSource::GeneratePrimaryVertex",
                  "GeneratePrimaryVertexError", FatalException, error_msg);
    }
    if (G4UniformRand() < solid_angle / fMaxSolidAngle / 1.1) {
      fCurrentSolidAngle = solid_angle;
      break;
    }
    fCurrentPos = fPositionGenerator->VGenerateOne();
  }
  fPosGenerated = true;
}

void GateSingleParticleSourceWindowTurbo::GeneratePrimaryVertex(
    G4Event *event) {
  if (not fSkip)
    GeneratePos();
  fPosGenerated = false;
  SetPhiTheta(fCurrentPos);
  G4ThreeVector direction;
  while (true) {
    direction = fDirectionGenerator->VGenerateOne();
    if (CheckPosDirValid(fCurrentPos, direction)) {
      break;
    }
  }
  G4PrimaryVertex *vertex = new G4PrimaryVertex(fCurrentPos, particle_time);

  // Set placement relative to attached volume
  // DD(particle_momentum_direction);

  G4double energy = fEnergyGenerator->VGenerateOne(fParticleDefinition);

  // one single particle
  auto *particle = new G4PrimaryParticle(fParticleDefinition);
  particle->SetKineticEnergy(energy);
  particle->SetMass(fMass);
  particle->SetMomentumDirection(direction);
  particle->SetCharge(fCharge);
  particle->SetWeight(1.0);
  if (fPolarizationFlag)
    particle->SetPolarization(fPolarization);

  // set vertex
  vertex->SetPrimary(particle);
  event->AddPrimaryVertex(vertex);
}
