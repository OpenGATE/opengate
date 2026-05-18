/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSingleParticleSourceWindowTurbo_h
#define GateSingleParticleSourceWindowTurbo_h

#include "GateSingleParticleSource.h"
#include <G4ThreeVector.hh>
#include <G4Types.hh>

class GateSingleParticleSourceWindowTurbo : public GateSingleParticleSource {
public:
  explicit GateSingleParticleSourceWindowTurbo(std::string mother_volume);
  ~GateSingleParticleSourceWindowTurbo() override = default;
  void GeneratePrimaryVertex(G4Event *event) override;
  void InitializeUserInfo(py::dict &user_info);
  G4double GetCurrentSolidAngle() const { return fCurrentSolidAngle; }
  void GeneratePos();
  void SetSkipMode(G4bool skip) { fSkip = skip; }
  G4bool PosGenerated() const { return fPosGenerated; }
  void SetParameters(G4double a1, G4double a2, G4double b1, G4double b2,
                     G4double plane_distance, G4double plane_phi);
  void SetMaxSolidAngle(G4double max_solid_angle) {
    fMaxSolidAngle = max_solid_angle;
  }
  G4double GetMaxSolidAngle() const { return fMaxSolidAngle; }
  G4double InitializeBeforeRun(G4double &act_ratio, G4double &max_solid_angle);

private:
  G4double GetSolidAngle(
      const G4ThreeVector &pos) const; // get solid angle for the window
  G4bool CheckPosDirValid(const G4ThreeVector &pos,
                          const G4ThreeVector &dir)
      const; // check if the ray can pass through the window
  void SetPhiTheta(
      const G4ThreeVector &pos) const; // set the phi and theta of the direction
                                       // distribution according to the position
  G4double fPlaneDistance{NAN};
  G4double fPlanePhi{NAN};
  G4double fSinPlanePhi{NAN}, fCosPlanePhi{NAN};
  G4double fA1{NAN}, fA2{NAN}, fB1{NAN}, fB2{NAN};
  G4double fMaxSolidAngle = 0;
  G4String fSourceName;
  G4double fCurrentSolidAngle;
  G4ThreeVector fCurrentPos;
  G4bool fSkip;
  G4int fThreadCountInit;
  G4int fSamplingCountInit;
  G4bool fPosGenerated = false;
  void ThreadFunc(size_t count, G4double *act_ratio_all_thread,
                  G4double *max_solid_angle_thread);
};

#endif // GateSingleParticleSourceWindowTurbo_h
