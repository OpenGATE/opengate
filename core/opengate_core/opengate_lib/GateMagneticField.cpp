/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateMagneticField.h"

// constructor
GateMagneticField::GateMagneticField(G4MagneticField *inner,
                                     const G4VSolid *solid,
                                     std::vector<G4ThreeVector> translations,
                                     std::vector<G4RotationMatrix> rotations,
                                     double deltaChordMM)
    : G4MagneticField(), GateField(solid, std::move(translations),
                                   std::move(rotations), deltaChordMM),
      m_inner(inner) {}

// override of G4MagneticField interface
void GateMagneticField::GetFieldValue(const G4double Point[4],
                                      G4double *Bfield) const {

  // get the global coordinates of the point and the transform of the containing
  // placement
  const G4ThreeVector worldPoint(Point[0], Point[1], Point[2]);

  // get the local coordinates of the point in the containing placement, and the
  // transform of that placement
  const G4AffineTransform *transform = nullptr;
  const G4ThreeVector localPoint =
      findContainingPlacement(worldPoint, transform);
  const G4double localPos[4] = {localPoint.x(), localPoint.y(), localPoint.z(),
                                Point[3]};

  // get the local field value from the inner field object
  G4double localB[3] = {0.0, 0.0, 0.0};
  m_inner->GetFieldValue(localPos, localB);

  // rotate the field back to world coordinates
  const G4ThreeVector worldB =
      rotateToWorld({localB[0], localB[1], localB[2]}, *transform);

  // copy the result to the output array
  Bfield[0] = worldB.x();
  Bfield[1] = worldB.y();
  Bfield[2] = worldB.z();
}
