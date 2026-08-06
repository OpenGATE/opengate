/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMappedElectricField_h
#define GateMappedElectricField_h

#include "GateMappedFieldBase.h"
#include <G4ElectroMagneticField.hh>

class G4LogicalVolume;

// grid-based mapped electric field
class GateMappedElectricField : public G4ElectroMagneticField,
                                public GateMappedFieldBase {
public:
  GateMappedElectricField(
      const G4LogicalVolume *logicalVolume,
      GateGridInterpolator::GridDefinition gridDef,
      GateGridInterpolator::FieldValues fieldValues,
      GateGridInterpolator::InterpolationMethod interpMethod);

  // returns [0, 0, 0, Ex, Ey, Ez]
  void GetFieldValue(const G4double Point[4], G4double *BEfield) const override;

  G4bool DoesFieldChangeEnergy() const override { return true; }
};

#endif // GateMappedElectricField_h
