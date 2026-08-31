/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUniformElectroMagneticField_h
#define GateUniformElectroMagneticField_h

#include <G4ElectroMagneticField.hh>
#include <G4ThreeVector.hh>

// Pure inner field class (Geant4-like): uniform electric and magnetic fields.
// This does NOT inherit from GateElectroMagneticField; it is a pure Geant4
// inner field that will be wrapped by GateElectroMagneticField in the Python
// field manager.
class GateUniformElectroMagneticField : public G4ElectroMagneticField {
public:
  GateUniformElectroMagneticField(G4ThreeVector e_field_vector,
                                  G4ThreeVector b_field_vector);

  void GetFieldValue(const G4double Point[4], G4double *BEfield) const override;

  G4bool DoesFieldChangeEnergy() const override { return true; }

private:
  G4ThreeVector m_e_field_vector;
  G4ThreeVector m_b_field_vector;
};

#endif // GateUniformElectroMagneticField_h