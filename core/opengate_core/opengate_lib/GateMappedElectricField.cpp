/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateMappedElectricField.h"

GateMappedElectricField::GateMappedElectricField(
    const G4VSolid *solid, std::vector<G4ThreeVector> translations,
    std::vector<G4RotationMatrix> rotations, double deltaChordMM,
    GateGridInterpolator::GridDefinition gridDef,
    GateGridInterpolator::FieldValues fieldValues,
    GateGridInterpolator::InterpolationMethod interpMethod)
    : G4ElectroMagneticField(),
      GateMappedFieldBase(solid, std::move(translations), std::move(rotations),
                          deltaChordMM, gridDef, std::move(fieldValues),
                          interpMethod) {}

void GateMappedElectricField::GetFieldValue(const G4double Point[4],
                                            G4double *BEfield) const {
  BEfield[0] = BEfield[1] = BEfield[2] = 0.0;
  computeFieldValue(Point, BEfield + 3,
                    3); // +3 points the output pointer to the E components
}
