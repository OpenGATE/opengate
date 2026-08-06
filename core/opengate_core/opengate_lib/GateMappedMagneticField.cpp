/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateMappedMagneticField.h"

GateMappedMagneticField::GateMappedMagneticField(
    const G4LogicalVolume *logicalVolume,
    GateGridInterpolator::GridDefinition gridDef,
    GateGridInterpolator::FieldValues fieldValues,
    GateGridInterpolator::InterpolationMethod interpMethod)
    : G4MagneticField(),
      GateMappedFieldBase(logicalVolume, gridDef, std::move(fieldValues),
                          interpMethod) {}

void GateMappedMagneticField::GetFieldValue(const G4double Point[4],
                                            G4double *Bfield) const {
  computeFieldValue(Point, Bfield, 3);
}
