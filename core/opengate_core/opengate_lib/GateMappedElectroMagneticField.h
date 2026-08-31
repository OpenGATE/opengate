/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMappedElectroMagneticField_h
#define GateMappedElectroMagneticField_h

#include "GateFieldBase.h"
#include "GateGridInterpolator.h"
#include <G4ElectroMagneticField.hh>
#include <vector>

class G4VSolid;

// grid-based mapped electromagnetic field with separate B and E grids
class GateMappedElectroMagneticField : public G4ElectroMagneticField,
                                       public GateFieldBase {
public:
  GateMappedElectroMagneticField(
      const G4VSolid *solid, std::vector<G4ThreeVector> translations,
      std::vector<G4RotationMatrix> rotations, double deltaChordMM,
      GateGridInterpolator::GridDefinition gridDefB,
      GateGridInterpolator::FieldValues fieldValuesB,
      GateGridInterpolator::GridDefinition gridDefE,
      GateGridInterpolator::FieldValues fieldValuesE,
      GateGridInterpolator::InterpolationMethod interpMethod);

  // returns [Bx, By, Bz, Ex, Ey, Ez]
  void GetFieldValue(const G4double Point[4], G4double *BEfield) const override;

  G4bool DoesFieldChangeEnergy() const override { return true; }

private:
  GateGridInterpolator m_interpolator_B;
  GateGridInterpolator m_interpolator_E;
};

#endif // GateMappedElectroMagneticField_h