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

GateSingleParticleSourceWindowTurbo::GateSingleParticleSourceWindowTurbo(
    std::string mother_volume)
    : GateSingleParticleSource(mother_volume) {}

GateSingleParticleSourceWindowTurbo::~GateSingleParticleSourceWindowTurbo() =
    default;

G4double solid_angle_pyramid(G4double a, G4double b, G4double d) {
  return 4 * atan(a * b / (2 * d * sqrt(a * a + b * b + 4 * d * d)));
}

G4double GateSingleParticleSourceWindowTurbo::GetSolidAngle(
    const G4ThreeVector &pos) const {

  // rotate with -plane_phi
  if (pos.x() * pos.x() + pos.y() * pos.y() >=
      plane_distance * plane_distance) {
    G4String error_msg = fmt::format(
        "position {} is outside the plane distance {} for source: {}", pos,
        plane_distance, turbo_source_name);
    G4Exception("GateSingleParticleSourceWindowTurbo::GetSolidAngle",
                "GetSolidAngleError", FatalException, error_msg);
  }

  G4double x0 = pos.x() * cos_plane_phi + pos.y() * sin_plane_phi;
  G4double y0 = -pos.x() * sin_plane_phi + pos.y() * cos_plane_phi;
  G4double a1_rel = a1 - y0;
  G4double a2_rel = a2 - y0;
  G4double b1_rel = b1 - pos.z();
  G4double b2_rel = b2 - pos.z();
  G4double d_rel = plane_distance - x0;
  G4double sa11 = solid_angle_pyramid(2 * a1_rel, 2 * b1_rel, d_rel);
  G4double sa12 = solid_angle_pyramid(2 * a1_rel, 2 * b2_rel, d_rel);
  G4double sa21 = solid_angle_pyramid(2 * a2_rel, 2 * b1_rel, d_rel);
  G4double sa22 = solid_angle_pyramid(2 * a2_rel, 2 * b2_rel, d_rel);
  G4double sa = sa11 + sa22 - sa12 - sa21;
  return fabs(sa * 0.25);
}

void GateSingleParticleSourceWindowTurbo::Initialize(py::dict &user_info) {
  // TODO: make this run in master thread before each run
  // and make the worker thread get info properly before each run
  a1 = DictGetDouble(user_info, "a1");
  a2 = DictGetDouble(user_info, "a2");
  b1 = DictGetDouble(user_info, "b1");
  b2 = DictGetDouble(user_info, "b2");
  plane_distance = DictGetDouble(user_info, "plane_distance");
  plane_phi = DictGetDouble(user_info, "plane_phi");
  sin_plane_phi = sin(plane_phi);
  cos_plane_phi = cos(plane_phi);
  turbo_source_name = DictGetStr(user_info, "name");

  act_ratio = DictGetDouble(user_info, "act_ratio");
  max_solid_angle = DictGetDouble(user_info, "max_solid_angle");
  if (not isnan(act_ratio) && not isnan(max_solid_angle) and act_ratio >= 0 and
      act_ratio <= 1 and max_solid_angle >= 0 and max_solid_angle <= 4 * M_PI) {
    G4cout << "Turbo source " << turbo_source_name
           << " already has act_ratio and max_solid_angle set." << G4endl;
    return;
  }

  if (not G4Threading::IsMasterThread()) {
    // TBD: should I check validity of act_ratio and max_solid_angle here or in
    // python side?
    if (isnan(act_ratio) || isnan(max_solid_angle)) {
      G4String error_msg =
          "activity ratio or max solid angle not set for source: ";
      G4String source_name = DictGetStr(user_info, "name");
      error_msg += source_name;
      G4Exception("GateSingleParticleSourceWindowTurbo::Initialize",
                  "InitializeError", FatalException, error_msg);
    }
    return;
  }

  G4int samplingCount = DictGetInt(user_info, "sampling_count");

  // TODO: implement random engine init in python
  // GateRandomEngine *theRandomEngine = GateRandomEngine::GetInstance();
  // if (!random_engine_initialized) {
  //   theRandomEngine->Initialize();
  //   random_engine_initialized = true;
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

  auto start_time = std::chrono::high_resolution_clock::now();
  G4double act_ratio_all = 0;
  G4ThreeVector pos;
  for (G4int i = 0; i < samplingCount; i++) {
    pos = fPositionGenerator->GenerateOne();
    G4double solid_angle = GetSolidAngle(pos);
    if (solid_angle > max_solid_angle)
      max_solid_angle = solid_angle;
    act_ratio_all += solid_angle / 4 / M_PI;
  }
  act_ratio = act_ratio_all / samplingCount;
  auto end_time = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
      end_time - start_time);
  G4String source_name = DictGetStr(user_info, "name");
  G4cout << "Activity Ratio of source " << source_name << " is "
         << std::scientific << std::setprecision(10) << act_ratio
         << std::defaultfloat << G4endl;
  G4cout << "Max Solid Angle of source " << source_name << " is "
         << std::scientific << std::setprecision(10) << max_solid_angle
         << std::defaultfloat << G4endl;
  G4cout << "Time used: " << duration.count() << " microseconds" << G4endl;
  // VerifyPhiTheta(samplingCount, 0.01);
  user_info["act_ratio"] = act_ratio;
  user_info["max_solid_angle"] = max_solid_angle;
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

  G4double x0 = pos.x() * cos_plane_phi + pos.y() * sin_plane_phi;
  G4double y0 = -pos.x() * sin_plane_phi + pos.y() * cos_plane_phi;
  G4double a1_rel = a1 - y0;
  G4double a2_rel = a2 - y0;
  G4double b1_rel = b1 - pos.z();
  G4double b2_rel = b2 - pos.z();
  G4double d_rel = plane_distance - x0;

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
  G4double phimin = atan2(a1_rel, d_rel) + plane_phi;
  G4double phimax = atan2(a2_rel, d_rel) + plane_phi;

  fDirectionGenerator->SetMinPhi(phimin + M_PI);
  fDirectionGenerator->SetMaxPhi(phimax + M_PI);
}

G4bool GateSingleParticleSourceWindowTurbo::CheckPosDirValid(
    const G4ThreeVector &pos, const G4ThreeVector &dir) const {
  // compare theta with cos2, to avoid complex calculation
  //   G4double cot2theta = std::copysign(1.0, dir.z()) * dir.z() * dir.z() /
  //                        (dir.x() * dir.x() + dir.y() * dir.y());

  G4double x0 = pos.x() * cos_plane_phi + pos.y() * sin_plane_phi;
  G4double y0 = -pos.x() * sin_plane_phi + pos.y() * cos_plane_phi;
  G4double a1_rel = a1 - y0;
  G4double a2_rel = a2 - y0;
  G4double b1_rel = b1 - pos.z();
  G4double b2_rel = b2 - pos.z();
  G4double d_rel = plane_distance - x0;
  G4double dir_x_rotated = dir.x() * cos_plane_phi + dir.y() * sin_plane_phi;
  G4double dir_y_rotated = -dir.x() * sin_plane_phi + dir.y() * cos_plane_phi;

  G4double intersect_b = d_rel / dir_x_rotated * dir.z() + pos.z();
  G4double intersect_a = d_rel / dir_x_rotated * dir_y_rotated + y0;
  return intersect_a <= a2 && intersect_a >= a1 && intersect_b <= b2 &&
         intersect_b >= b1;
}

void GateSingleParticleSourceWindowTurbo::GeneratePrimaryVertex(
    G4Event *event) {

  G4ThreeVector position = fPositionGenerator->GenerateOne();

  // probability of the position is valid should be proportional to the solid
  // angle
  while (true) {
    G4double solid_angle = GetSolidAngle(position);
    if (solid_angle > max_solid_angle * 1.1) {
      G4String error_msg =
          "solid angle of position is larger than max solid angle for source: ";
      error_msg += turbo_source_name;
      error_msg += "\nyou may increase max solid angle and try again";
      G4Exception("GateWindowTurboSource::GeneratePrimaryVertex",
                  "GeneratePrimaryVertexError", FatalException, error_msg);
    }
    if (G4UniformRand() < solid_angle / max_solid_angle / 1.1) {
      break;
    }
    position = fPositionGenerator->GenerateOne();
  }

  SetPhiTheta(position);
  G4ThreeVector direction;
  while (true) {
    direction = fDirectionGenerator->GenerateOne();
    if (CheckPosDirValid(position, direction)) {
      break;
    }
  }
  G4PrimaryVertex *vertex = new G4PrimaryVertex(position, particle_time);

  // Set placement relative to attached volume
  // DD(particle_momentum_direction);

  G4double energy = fEnergyGenerator->GenerateOne(fParticleDefinition);

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
