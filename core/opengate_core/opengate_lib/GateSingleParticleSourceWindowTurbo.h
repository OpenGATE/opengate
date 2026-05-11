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
  G4double GetSolidAngle(
      const G4ThreeVector &pos) const; // get solid angle for the window
  G4bool CheckPosDirValid(const G4ThreeVector &pos,
                          const G4ThreeVector &dir)
      const; // check if the ray can pass through the window
  void SetPhiTheta(
      const G4ThreeVector &pos) const; // set the phi and theta of the direction
                                       // distribution according to the position
  G4double plane_distance{NAN};
  G4double plane_phi{NAN};
  G4double sin_plane_phi{NAN}, cos_plane_phi{NAN};
  G4double a1{NAN}, a2{NAN}, b1{NAN}, b2{NAN};
  G4double act_ratio = 1;
  G4double max_solid_angle = 0;
  G4String turbo_source_name;
};

#endif // GateSingleParticleSourceWindowTurbo_h
