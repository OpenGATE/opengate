/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateMappedElectroMagneticField.h"

GateMappedElectroMagneticField::GateMappedElectroMagneticField(
    const G4VSolid *solid, std::vector<G4ThreeVector> translations,
    std::vector<G4RotationMatrix> rotations, double deltaChordMM,
    GateGridInterpolator::GridDefinition gridDefB,
    GateGridInterpolator::FieldValues fieldValuesB,
    GateGridInterpolator::GridDefinition gridDefE,
    GateGridInterpolator::FieldValues fieldValuesE,
    GateGridInterpolator::InterpolationMethod interpMethod)
    : G4ElectroMagneticField(),
      GateFieldBase(solid, std::move(translations), std::move(rotations),
                    deltaChordMM),
      m_interpolator_B(gridDefB, std::move(fieldValuesB), interpMethod),
      m_interpolator_E(gridDefE, std::move(fieldValuesE), interpMethod) {}

void GateMappedElectroMagneticField::GetFieldValue(const G4double Point[4],
                                                   G4double *BEfield) const {
  // localFieldFunc interpolates B and E separately, then combines them
  auto localFieldFunc = [this](const G4double pos[4], G4double *f) {
    double B[3] = {0.0, 0.0, 0.0};
    double E[3] = {0.0, 0.0, 0.0};
    m_interpolator_B.Interpolate(pos[0], pos[1], pos[2], B);
    m_interpolator_E.Interpolate(pos[0], pos[1], pos[2], E);
    f[0] = B[0];
    f[1] = B[1];
    f[2] = B[2];
    f[3] = E[0];
    f[4] = E[1];
    f[5] = E[2];
  };

  applyTransforms(Point, BEfield, 6, localFieldFunc);
}
