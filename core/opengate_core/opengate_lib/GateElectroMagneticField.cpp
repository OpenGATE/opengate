/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateElectroMagneticField.h"

GateElectroMagneticField::GateElectroMagneticField(
    G4ElectroMagneticField *inner, const G4VSolid *solid,
    std::vector<G4ThreeVector> translations,
    std::vector<G4RotationMatrix> rotations, double deltaChordMM)
    : G4ElectroMagneticField(), GateField(solid, std::move(translations),
                                          std::move(rotations), deltaChordMM),
      m_inner(inner) {}

void GateElectroMagneticField::GetFieldValue(const G4double Point[4],
                                             G4double *BEfield) const {
  const G4ThreeVector worldPoint(Point[0], Point[1], Point[2]);

  const G4AffineTransform *transform = nullptr;
  const G4ThreeVector localPoint =
      findContainingPlacement(worldPoint, transform);
  const G4double localPos[4] = {localPoint.x(), localPoint.y(), localPoint.z(),
                                Point[3]};

  G4double localBE[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
  m_inner->GetFieldValue(localPos, localBE);

  const G4ThreeVector worldB =
      rotateToWorld({localBE[0], localBE[1], localBE[2]}, *transform);
  const G4ThreeVector worldE =
      rotateToWorld({localBE[3], localBE[4], localBE[5]}, *transform);

  BEfield[0] = worldB.x();
  BEfield[1] = worldB.y();
  BEfield[2] = worldB.z();
  BEfield[3] = worldE.x();
  BEfield[4] = worldE.y();
  BEfield[5] = worldE.z();
}
