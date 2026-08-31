/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniformElectroMagneticField.h"

GateUniformElectroMagneticField::GateUniformElectroMagneticField(
    G4ThreeVector e_field_vector, G4ThreeVector b_field_vector)
    : G4ElectroMagneticField(), m_e_field_vector(e_field_vector),
      m_b_field_vector(b_field_vector) {}

void GateUniformElectroMagneticField::GetFieldValue(const G4double Point[4],
                                                    G4double *BEfield) const {
  // Uniform field does not depend on position or time.
  BEfield[0] = m_b_field_vector.x();
  BEfield[1] = m_b_field_vector.y();
  BEfield[2] = m_b_field_vector.z();
  BEfield[3] = m_e_field_vector.x();
  BEfield[4] = m_e_field_vector.y();
  BEfield[5] = m_e_field_vector.z();
}
