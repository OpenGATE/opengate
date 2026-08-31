/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateFieldBase_h
#define GateFieldBase_h

#include <G4AffineTransform.hh>
#include <G4RotationMatrix.hh>
#include <G4ThreeVector.hh>
#include <G4Types.hh>
#include <vector>

class G4VSolid;

// Shared base class for all GATE field types
//  - stores the world-to-local transforms of every physical placement of the
//  logical volume
//  - handles the full coordinate transform journey for GetFieldValue
class GateFieldBase {
public:
  // constructor
  GateFieldBase(const G4VSolid *solid, std::vector<G4ThreeVector> translations,
                std::vector<G4RotationMatrix> rotations, double deltaChordMM);

  // update the transforms (e.g. after a geometry change between runs)
  void SetTransforms(std::vector<G4ThreeVector> translations,
                     std::vector<G4RotationMatrix> rotations);

protected:
  // LocalFieldFn is expected to be something like:
  //   void getLocalField(const G4double localPos[4], G4double *field);
  // which fills the field array with the local field value at the given
  // localPos.
  template <typename LocalFieldFn>

  // Get the field value at the given world point by transforming to local
  // coordinates, calling getLocalField to fill the field value in local frame,
  // and then rotating the field vector(s) back to world frame
  void applyTransforms(const G4double Point[4], G4double *field,
                       int nComponents, LocalFieldFn getLocalField) const {
    const G4ThreeVector worldPt(Point[0], Point[1], Point[2]);
    const G4AffineTransform *tr = nullptr;
    const G4ThreeVector localPt = findContainingPlacement(worldPt, tr);
    const G4double localPos[4] = {localPt.x(), localPt.y(), localPt.z(),
                                  Point[3]};

    getLocalField(localPos, field);

    for (int i = 0; i < nComponents; i += 3) {
      const G4ThreeVector v = rotateToWorld(
          G4ThreeVector(field[i], field[i + 1], field[i + 2]), *tr);
      field[i] = v.x();
      field[i + 1] = v.y();
      field[i + 2] = v.z();
    }
  }

private:
  // find the local coordinates of worldPoint in the containing placement of the
  // field's logical volume
  G4ThreeVector
  findContainingPlacement(const G4ThreeVector &worldPoint,
                          const G4AffineTransform *&outTransform) const;

  // rotate a field vector from local to world coordinates using the given
  // transform
  static G4ThreeVector rotateToWorld(const G4ThreeVector &localField,
                                     const G4AffineTransform &transform);

  const G4VSolid *m_solid;
  double m_fallbackFatalDistanceMM;
  std::vector<G4AffineTransform> m_transforms;

  static constexpr double kMaxCurvatureRadiusMM = 100.0e3;
};

#endif // GateFieldBase_h
