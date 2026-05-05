/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateMagneticField_h
#define GateMagneticField_h

#include "G4MagneticField.hh"
#include "G4RotationMatrix.hh"
#include "G4ThreeVector.hh"
#include "GateField.h"
#include <vector>

class G4VSolid;

// GATE wrapper for G4MagneticField that transforms the query point to the local
// coordinates of the physical volume(s) the field is attached to, then
// delegates to the inner field class to get the field value, and finally
// transforms the field vector back to world coordinates.

// wrapper for an internal G4MagneticField converted to local coordinates
class GateMagneticField : public G4MagneticField, protected GateField {
public:
  // constructor — deltaChordMM is the chord-finder tolerance (delta_chord),
  // forwarded to GateField to compute the fallback-fatal distance internally.
  GateMagneticField(G4MagneticField *inner, // wrapped inner field
                    const G4VSolid *solid,  // solid of the logical volume the
                                            // field is attached to
                    std::vector<G4ThreeVector>
                        translations, // translations of the physical placements
                    std::vector<G4RotationMatrix>
                        rotations, // rotations of the physical placements of
                                   // the logical volume
                    double deltaChordMM);

  // override of G4MagneticField interface
  void GetFieldValue(const G4double Point[4], G4double *Bfield) const override;

  // forward override of GateField::SetTransforms
  inline void SetTransforms(std::vector<G4ThreeVector> translations,
                            std::vector<G4RotationMatrix> rotations) {
    GateField::SetTransforms(std::move(translations), std::move(rotations));
  }

private:
  G4MagneticField *m_inner; // wrapped inner field
};

#endif // GateMagneticField_h
