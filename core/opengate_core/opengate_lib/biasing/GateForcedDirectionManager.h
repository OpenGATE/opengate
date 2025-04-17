/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateForcedDirectionManager_h
#define GateForcedDirectionManager_h

#include "../GateAcceptanceAngleSingleVolume.h"
#include "../GateHelpers.h"

class GateForcedDirectionManager {
public:
  GateForcedDirectionManager();

  ~GateForcedDirectionManager();

  // enum AAPolicyType { AAZeroEnergy, AASkipEvent, AAUndefined };

  void Initialize(py::dict user_info, bool is_valid_type);

  void InitializeForcedDirection();

  unsigned long GetNumberOfNotAcceptedEvents() const;

  bool IsEnabled() const { return fEnabledFlag; }

  G4ThreeVector GenerateForcedDirection(G4ThreeVector position,
                                        bool &zero_energy_flag, double &weight);

  G4ThreeVector SampleDirectionWithinCone(double &theta);

  std::map<std::string, std::string> fAcceptanceAngleParam;
  std::vector<GateAcceptanceAngleSingleVolume *> fAATesters{};
  std::vector<std::string> fAcceptanceAngleVolumeNames;
  bool fEnabledFlag;
  unsigned long fNotAcceptedEvents;
  unsigned long fMaxNotAcceptedEvents;
  int fAALastRunId;

  double fNormalAngleTolerance;
  G4ThreeVector fNormalVector;
  G4AffineTransform fAATransform;
  G4RotationMatrix *fAARotation;
  G4RotationMatrix fAARotationInverse;
  G4VSolid *fAASolid;
  G4Navigator *fAANavigator;

  double fSinThetaMax;
  double fCosThetaMax;
  G4ThreeVector fU1;
  G4ThreeVector fU2;
  double fWeight;
};

#endif // GateForcedDirectionManager_h
