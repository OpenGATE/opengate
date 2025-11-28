/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAcceptanceAngleSingleVolume_h
#define GateAcceptanceAngleSingleVolume_h

#include "G4AffineTransform.hh"
#include "GateHelpers.h"

class GateAcceptanceAngleSingleVolume {
public:
  GateAcceptanceAngleSingleVolume(
      const std::string &volume,
      const std::map<std::string, std::string> &param);

  ~GateAcceptanceAngleSingleVolume();

  bool TestIfAccept(const G4ThreeVector &position,
                    const G4ThreeVector &momentum_direction) const;

  void PrepareCheck(const G4ThreeVector &position);

  bool TestDirection(const G4ThreeVector &momentum_direction) const;

  void UpdateTransform();

protected:
  std::string fAcceptanceAngleVolumeName;
  bool fEnableIntersectionCheck;
  bool fEnableAngleCheck;

  // Raw angles kept for debug/logging if needed
  double fAngleToleranceMax;
  double fAngleToleranceMin;
  double fAngleToleranceProximal;
  double fAngleCheckProximityDistance;

  // Cached Cosines for performance
  double fCosToleranceMax;
  double fCosToleranceMin;
  double fCosToleranceProximal;

  // Local coordinates
  G4ThreeVector fAngleReferenceVector;

  // World coordinates (cached)
  G4ThreeVector fGlobalAngleReferenceVector;

  // Cache local position to allow PrepareCheck+TestDirection instead of
  // TestIfAccept
  G4ThreeVector fCachedLocalPosition;

  G4AffineTransform fAATransform;
  G4RotationMatrix *fAARotation;
  G4VSolid *fAASolid;
  G4Navigator *fAANavigator;
};

#endif // GateAcceptanceAngleSingleVolume_h
