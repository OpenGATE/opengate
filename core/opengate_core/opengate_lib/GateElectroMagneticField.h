/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateElectroMagneticField_h
#define GateElectroMagneticField_h

#include "GateFieldBase.h"
#include <G4ElectroMagneticField.hh>
#include <vector>

class G4VSolid;

// GATE wrapper for G4ElectroMagneticField.
class GateElectroMagneticField : public G4ElectroMagneticField,
                                 public GateFieldBase {
public:
  // constructor
  GateElectroMagneticField(G4ElectroMagneticField *inner, const G4VSolid *solid,
                           std::vector<G4ThreeVector> translations,
                           std::vector<G4RotationMatrix> rotations,
                           double deltaChordMM);

  // override GetFieldValue to apply the coordinate transforms
  void GetFieldValue(const G4double Point[4], G4double *BEfield) const override;

  // override DoesFieldChangeEnergy to return true for electro-magnetic fields
  G4bool DoesFieldChangeEnergy() const override { return true; }

private:
  // the inner field in the volume's local frame
  G4ElectroMagneticField *m_inner;
};

#endif // GateElectroMagneticField_h
