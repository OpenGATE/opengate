/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateForcedDirectionManager_h
#define GateForcedDirectionManager_h

#include <G4AffineTransform.hh>
#include <G4VSolid.hh>

class GateForcedDirectionManager {
public:
  GateForcedDirectionManager();

  ~GateForcedDirectionManager();

  void Initialize(const std::map<std::string, std::string> &user_info,
                  bool is_valid_type);

  void InitializeForcedDirection();

  bool IsEnabled() const { return fEnabledFlag; }

  G4ThreeVector GenerateForcedDirection(const G4ThreeVector &position,
                                        bool &zero_energy_flag, double &weight);

  // sample a direction in the cone; weight: the weight of this direction
  // (constant with the uniform sampling)
  G4ThreeVector SampleDirectionWithinCone(double &theta, double &weight) const;

  std::vector<std::string> fAcceptanceAngleVolumeNames;
  bool fEnabledFlag;
  int fFDLastRunId;
  bool fEnableIntersectionCheck;

  double fAngleToleranceMax;
  double fAngleToleranceMin;
  G4ThreeVector fAngleReferenceVector;
  G4AffineTransform fFDTransformWorldToVolume;
  G4RotationMatrix *fFDRotation;
  G4RotationMatrix fAARotationInverse;
  G4VSolid *fSolid;

  double fSinThetaMax;
  double fCosThetaMax;
  double fSinThetaMin;
  double fCosThetaMin;
  G4ThreeVector fU1;
  G4ThreeVector fU2;
  double fWeight;

  // sampling of u = 1 - cos(theta) in the cone: "uniform" (pdf constant,
  // weight constant) or "log" (pdf ~ 1 / (u + u0), u0 = 1 - cos(scale):
  // more directions near the reference vector, weight (u + u0) L / 2)
  bool fLogSamplingFlag;
  double fU0;
  double fUMin;
  double fLogRange;
};

#endif // GateForcedDirectionManager_h
