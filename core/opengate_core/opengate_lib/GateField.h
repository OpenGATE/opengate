/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateField_h
#define GateField_h

#include "G4AffineTransform.hh"
#include "G4RotationMatrix.hh"
#include "G4ThreeVector.hh"
#include <vector>

// Forward declaration to avoid including the full header.
class G4VSolid;

// Helper base class for fields in GATE:
// - stores the world-to-local transforms of every physical
//   placement of the logical volume the field is attached to.
// - provides the coordinate conversions needed to evaluate fields in each
//   placement's local frame and rotate the result back to world.
class GateField {

public:
  // constructor — deltaChordMM is the chord-finder tolerance (delta_chord),
  // used to compute the fallback-fatal distance internally.
  GateField(const G4VSolid *solid, std::vector<G4ThreeVector> translations,
            std::vector<G4RotationMatrix> rotations, double deltaChordMM);

  // update the transforms (e.g. after a geometry change between runs)
  void SetTransforms(std::vector<G4ThreeVector> translations,
                     std::vector<G4RotationMatrix> rotations);

protected:
  // find the local coordinates of worldPoint in the containing placement, and
  // return the world-to-local transform of that placement in outTransform.
  G4ThreeVector
  findContainingPlacement(const G4ThreeVector &worldPoint,
                          const G4AffineTransform *&outTransform) const;

  // rotate a field vector from local to world coordinates using the given
  // transform.
  static G4ThreeVector rotateToWorld(const G4ThreeVector &localField,
                                     const G4AffineTransform &transform);

  const G4VSolid
      *m_solid; // solid of the logical volume the field is attached to

  double
      m_fallbackFatalDistanceMM; // computed from deltaChordMM at construction

  std::vector<G4AffineTransform> m_transforms; // one per physical placement

  // Upper bound on the radius of curvature [mm] used to derive
  // the fallback-fatal distance.
  static constexpr double kMaxCurvatureRadiusMM = 100.0e3;
};

#endif // GateField_h
