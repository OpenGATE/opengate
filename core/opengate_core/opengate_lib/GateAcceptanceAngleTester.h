/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAcceptanceAngleTester_h
#define GateAcceptanceAngleTester_h

#include "G4AffineTransform.hh"
#include "GateHelpers.h"

class GateAcceptanceAngleTester {
public:
  GateAcceptanceAngleTester(std::string volume,
                            std::map<std::string, std::string> &param);

  ~GateAcceptanceAngleTester();

  bool TestIfAccept(const G4ThreeVector &position,
                    const G4ThreeVector &momentum_direction);

  void UpdateTransform();

protected:
  std::string fAcceptanceAngleVolumeName;
  bool fIntersectionFlag;
  bool fNormalFlag;
  double fNormalAngleTolerance;
  G4ThreeVector fNormalVector;
  G4AffineTransform fAATransform;
  G4RotationMatrix *fAARotation;
  G4VSolid *fAASolid;
  G4Navigator *fAANavigator;
};

#endif // GateAcceptanceAngleTester_h
