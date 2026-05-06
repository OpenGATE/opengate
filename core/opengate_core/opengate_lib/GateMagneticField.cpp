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
    : G4MagneticField(), GateFieldBase(solid, std::move(translations),
                                       std::move(rotations), deltaChordMM),
      m_inner(inner) {}

void GateMagneticField::GetFieldValue(const G4double Point[4],
                                      G4double *Bfield) const {
  // localFieldFunc is a lambda that captures 'this' and calls
  // m_inner->GetFieldValue
  auto localFieldFunc = [this](const G4double pos[4], G4double *f) {
    m_inner->GetFieldValue(pos, f);
  };

  applyTransforms(Point, Bfield, 3, localFieldFunc);
}
