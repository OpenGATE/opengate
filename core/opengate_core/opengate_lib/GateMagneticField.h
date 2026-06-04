/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMagneticField_h
#define GateMagneticField_h

#include "G4MagneticField.hh"
#include "GateFieldBase.h"
#include <vector>

class G4VSolid;

// GATE wrapper for G4MagneticField
class GateMagneticField : public G4MagneticField, public GateFieldBase {
public:
  // constructor
  GateMagneticField(G4MagneticField *inner, const G4VSolid *solid,
                    std::vector<G4ThreeVector> translations,
                    std::vector<G4RotationMatrix> rotations,
                    double deltaChordMM);

  // override GetFieldValue to apply the coordinate transforms
  void GetFieldValue(const G4double Point[4], G4double *Bfield) const override;

private:
  // the inner field in the volume's local frame
  G4MagneticField *m_inner;
};

#endif // GateMagneticField_h
