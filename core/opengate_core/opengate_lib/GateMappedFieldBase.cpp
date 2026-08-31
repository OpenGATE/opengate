/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateMappedFieldBase.h"

// constructor
GateMappedFieldBase::GateMappedFieldBase(
    const G4VSolid *solid, std::vector<G4ThreeVector> translations,
    std::vector<G4RotationMatrix> rotations, double deltaChordMM,
    GateGridInterpolator::GridDefinition gridDef,
    GateGridInterpolator::FieldValues fieldValues,
    GateGridInterpolator::InterpolationMethod interpMethod)
    : GateFieldBase(solid, std::move(translations), std::move(rotations),
                    deltaChordMM),
      m_interpolator(gridDef, std::move(fieldValues), interpMethod) {}

// Compute field value at world point: transform to local, interpolate, rotate
// back
void GateMappedFieldBase::computeFieldValue(const G4double Point[4],
                                            G4double *field,
                                            int nComponents) const {

  // localFieldFunc is a lambda that captures 'this' and calls
  // m_interpolator.Interpolate with the local point coordinates
  auto localFieldFunc = [this](const G4double pos[4], G4double *f) {
    m_interpolator.Interpolate(pos[0], pos[1], pos[2], f);
  };

  applyTransforms(Point, field, nComponents, localFieldFunc);
}
