/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSingleParticleSourceWindowTurbo.h"

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