/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMappedFieldBase_h
#define GateMappedFieldBase_h

#include "GateFieldBase.h"
#include "GateGridInterpolator.h"

class G4LogicalVolume;

// base class for mapped fields that use grid interpolation
class GateMappedFieldBase : public GateFieldBase {
public:
  // constructor
  GateMappedFieldBase(const G4LogicalVolume *logicalVolume,
                      GateGridInterpolator::GridDefinition gridDef,
                      GateGridInterpolator::FieldValues fieldValues,
                      GateGridInterpolator::InterpolationMethod interpMethod);

protected:
  // transform Point to local frame, interpolate, rotate result back to world.
  void computeFieldValue(const G4double Point[4], G4double *field,
                         int nComponents) const;

private:
  GateGridInterpolator m_interpolator;
};

#endif // GateMappedFieldBase_h
