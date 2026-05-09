/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSingleParticleSourceWindowTurbo_h
#define GateSingleParticleSourceWindowTurbo_h

#include "GateSingleParticleSource.h"

class GateSingleParticleSourceWindowTurbo : public GateSingleParticleSource {
public:
  explicit GateSingleParticleSourceWindowTurbo(std::string mother_volume);
  ~GateSingleParticleSourceWindowTurbo() override;
  void GeneratePrimaryVertex(G4Event *event) override;
  void Initialize(py::dict &user_info);

private:
  G4double GetSolidAngle(const G4ThreeVector &pos) const;
  G4double plane_distance{NAN};
  G4double plane_phi{NAN};
  G4double sin_plane_phi{NAN}, cos_plane_phi{NAN};
  G4double a1{NAN}, a2{NAN}, b1{NAN}, b2{NAN};
  G4double act_ratio = 1;
  G4double max_solid_angle = 0;
  G4bool act_ratio_set;
  G4bool max_solid_angle_set;
  // void SetA1(G4double a) { a1 = a; };
  // void SetA2(G4double a) { a2 = a; };
  // void SetB1(G4double b) { b1 = b; };
  // void SetB2(G4double b) { b2 = b; };
  // void SetPlaneDistance(G4double distance) { plane_distance = distance; };
  // void SetPlanePhi(G4double phi) {
  //   plane_phi = phi;
  //   sin_plane_phi = sin(phi);
  //   cos_plane_phi = cos(phi);
  // };
};

#endif // GateSingleParticleSourceWindowTurbo_h
