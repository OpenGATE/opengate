/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSingleParticleSourceWindowTurbo.h"
#include "G4Threading.hh"
#include "GateHelpersDict.h"

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
  // if (pos.mag2() >= mPth1.mag2() || pos.mag2() >= mPth2.mag2() ||
  //     pos.mag2() >= mPphi1.mag2() || pos.mag2() >= mPphi2.mag2()) {
  //   G4Exception("GateWindowTurboSource::GetSolidAngle", "GetSolidAngleError",
  //               FatalException, "source position not inside edge point");
  // }

  // rotate with -plane_phi

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
  a1 = DictGetDouble(user_info, "a1");
  a2 = DictGetDouble(user_info, "a2");
  b1 = DictGetDouble(user_info, "b1");
  b2 = DictGetDouble(user_info, "b2");
  plane_distance = DictGetDouble(user_info, "plane_distance");
  plane_phi = DictGetDouble(user_info, "plane_phi");
  sin_plane_phi = sin(plane_phi);
  cos_plane_phi = cos(plane_phi);

  if (not G4Threading::IsMasterThread()) {
    act_ratio = DictGetDouble(user_info, "act_ratio");
    max_solid_angle = DictGetDouble(user_info, "max_solid_angle");
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
  act_ratio_set = true;
  max_solid_angle_set = true;
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

void GateSingleParticleSourceWindowTurbo::GeneratePrimaryVertex(
    G4Event *event) {
  if (not(act_ratio_set and max_solid_angle_set)) {
    G4String error_msg =
        "activity ratio or max solid angle not set for source: ";
    error_msg += m_name;
    G4Exception("GateWindowTurboSource::GeneratePrimaryVertex",
                "GeneratePrimaryVertexError", FatalException, error_msg);
  }
  G4ThreeVector position = m_posSPS->GenerateOne();

  // probability of the position is valid should be proportional to the solid
  // angle
  while (true) {
    G4double solid_angle = GetSolidAngle(position);
    if (solid_angle > max_solid_angle * 1.1) {
      G4String error_msg =
          "solid angle of position is larger than max solid angle for source: ";
      error_msg += m_name;
      error_msg += "\nyou may increase max solid angle and try again";
      G4Exception("GateWindowTurboSource::GeneratePrimaryVertex",
                  "GeneratePrimaryVertexError", FatalException, error_msg);
    }
    if (G4UniformRand() < solid_angle / max_solid_angle / 1.1) {
      break;
    }
    position = m_posSPS->GenerateOne();
  }

  ChangeParticlePositionRelativeToAttachedVolume(position);
  SetPhiTheta(position);
  G4ThreeVector direction;
  while (true) {
    direction = m_angSPS->GenerateOne();
    if (CheckPosDirValid(position, direction)) {
      break;
    }
  }
  G4PrimaryVertex *vertex = new G4PrimaryVertex(position, GetParticleTime());

  // Set placement relative to attached volume
  // DD(particle_momentum_direction);

  G4double particle_energy = 0;
  particle_energy = m_eneSPS->GenerateOne(GetParticleDefinition());
  mEnergy = particle_energy; // because particle_energy is private

  G4double mass = GetParticleDefinition()->GetPDGMass();
  G4double energy = particle_energy + mass;
  G4double pmom = std::sqrt(energy * energy - mass * mass);
  G4double px = pmom * direction.x();
  G4double py = pmom * direction.y();
  G4double pz = pmom * direction.z();

  G4PrimaryParticle *particle =
      new G4PrimaryParticle(GetParticleDefinition(), px, py, pz);
  particle->SetMass(mass);
  particle->SetCharge(GetParticleDefinition()->GetPDGCharge());
  particle->SetPolarization(GetParticlePolarization().x(),
                            GetParticlePolarization().y(),
                            GetParticlePolarization().z());

  G4double particle_weight = GetBiasRndm()->GetBiasWeight();
  particle->SetWeight(particle_weight);

  // Add one particle
  vertex->SetPrimary(particle);

  // Verbose
  if (nVerboseLevel > 1) {
    G4cout << "Particle name: " << GetParticleDefinition()->GetParticleName()
           << G4endl;
    G4cout << "       Energy: " << particle_energy << G4endl;
    G4cout << "     Position: " << particle_position << G4endl;
    G4cout << "    Direction: " << direction << G4endl;
  }
  if (nVerboseLevel > 2) {
    G4cout << "Creating primaries and assigning to vertex\n";
  }

  event->AddPrimaryVertex(vertex);
}