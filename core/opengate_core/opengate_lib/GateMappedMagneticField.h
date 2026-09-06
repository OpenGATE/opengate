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

class G4LogicalVolume;

// grid-based mapped magnetic field.
class GateMappedMagneticField : public G4MagneticField,
                                public GateMappedFieldBase {
public:
  GateMappedMagneticField(
      const G4LogicalVolume *logicalVolume,
      GateGridInterpolator::GridDefinition gridDef,
      GateGridInterpolator::FieldValues fieldValues,
      GateGridInterpolator::InterpolationMethod interpMethod);

  void GetFieldValue(const G4double Point[4], G4double *Bfield) const override;
};

#endif // GateMappedMagneticField_h
