/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamAcceptanceAngleTester_h
#define GamAcceptanceAngleTester_h

#include "G4AffineTransform.hh"
#include "GamHelpers.h"

class GamAcceptanceAngleTester {
public:

    GamAcceptanceAngleTester(std::string volume, std::map<std::string, std::string> &param);

    bool TestIfAccept(G4ThreeVector &position, G4ThreeVector &momentum_direction);

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

#endif // GamAcceptanceAngleTester_h
