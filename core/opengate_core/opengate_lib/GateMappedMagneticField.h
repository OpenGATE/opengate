/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMappedMagneticField_h
#define GateMappedMagneticField_h

#include "GateMappedFieldBase.h"
#include <G4MagneticField.hh>
#include <vector>

class G4VSolid;

// grid-based mapped magnetic field.
class GateMappedMagneticField : public G4MagneticField,
                                public GateMappedFieldBase {
public:
  GateMappedMagneticField(
      const G4VSolid *solid, std::vector<G4ThreeVector> translations,
      std::vector<G4RotationMatrix> rotations, double deltaChordMM,
      GateGridInterpolator::GridDefinition gridDef,
      GateGridInterpolator::FieldValues fieldValues,
      GateGridInterpolator::InterpolationMethod interpMethod);

  void GetFieldValue(const G4double Point[4], G4double *Bfield) const override;
};

#endif // GateMappedMagneticField_h
