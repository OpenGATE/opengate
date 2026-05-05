/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateElectroMagneticField_h
#define GateElectroMagneticField_h

#include "G4ElectroMagneticField.hh"
#include "G4RotationMatrix.hh"
#include "G4ThreeVector.hh"
#include "GateField.h"
#include <vector>

class G4VSolid;

// GATE wrapper for G4ElectroMagneticField
class GateElectroMagneticField : public G4ElectroMagneticField,
                                 protected GateField {
public:
  GateElectroMagneticField(G4ElectroMagneticField *inner, const G4VSolid *solid,
                           std::vector<G4ThreeVector> translations,
                           std::vector<G4RotationMatrix> rotations,
                           double deltaChordMM);

  void GetFieldValue(const G4double Point[4], G4double *BEfield) const override;

  G4bool DoesFieldChangeEnergy() const override { return true; }

  inline void SetTransforms(std::vector<G4ThreeVector> translations,
                            std::vector<G4RotationMatrix> rotations) {
    GateField::SetTransforms(std::move(translations), std::move(rotations));
  }

private:
  G4ElectroMagneticField *m_inner;
};

#endif // GateElectroMagneticField_h
