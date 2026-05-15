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

class GateSingleParticleSourceWindowTurbo : public GateSingleParticleSource {
public:
  explicit GateSingleParticleSourceWindowTurbo(std::string mother_volume);
  ~GateSingleParticleSourceWindowTurbo() override = default;
  void GeneratePrimaryVertex(G4Event *event) override;
  void Initialize(py::dict &user_info, std::string name);
  G4double GetActRatio() const { return fActRatio; }
  G4double GetCurrentSolidAngle() const { return fCurrentSolidAngle; }
  void GeneratePos();
  void SetSkipMode(G4bool skip) { fSkip = skip; }
  G4bool GetPosGenerated() const { return fPosGenerated; }

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
  G4double fActRatio = 1;
  G4double fMaxSolidAngle = 0;
  G4String fSourceName;
  G4double fCurrentSolidAngle;
  G4ThreeVector fCurrentPos;
  G4bool fSkip;
  G4bool fPosGenerated = false;
  void ThreadFunc(size_t count, G4double *act_ratio_all_thread,
                  G4double *max_solid_angle_thread);
};

#endif // GateSingleParticleSourceWindowTurbo_h
