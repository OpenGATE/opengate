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

  void UpdateTransform();

protected:
  std::string fAcceptanceAngleVolumeName;
  bool fIntersectionFlag;
  bool fNormalFlag;
  double fNormalAngleTolerance;
  double fMinDistanceNormalAngleTolerance;
  G4ThreeVector fNormalVector;
  G4AffineTransform fAATransform;
  G4RotationMatrix *fAARotation;
  G4VSolid *fAASolid;
  G4Navigator *fAANavigator;
};

#endif // GateAcceptanceAngleSingleVolume_h
