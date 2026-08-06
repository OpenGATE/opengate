/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateFieldBase_h
#define GateFieldBase_h

#include <G4AffineTransform.hh>
#include <G4ThreeVector.hh>
#include <G4Types.hh>

class G4LogicalVolume;

// Shared base class for all GATE field types
//
// A GATE field is defined in the local frame of the logical volume it is
// attached to. The world-to-local transform is read from
// Geant4's navigation history on every query, so it always describes the
// placement the track actually occupies.
class GateFieldBase {
public:
  // constructor
  explicit GateFieldBase(const G4LogicalVolume *logicalVolume);

protected:
  // LocalFieldFn is expected to be something like:
  //   void getLocalField(const G4double localPos[4], G4double *field);
  // which fills the field array with the local field value at the given
  // localPos.
  //
  // Get the field value at the given world point by transforming to local
  // coordinates, calling getLocalField to fill the field value in local frame,
  // and then rotating the field vector(s) back to world frame
  template <typename LocalFieldFn>
  void applyTransforms(const G4double Point[4], G4double *field,
                       int nComponents, LocalFieldFn getLocalField) const {
    const G4AffineTransform worldToLocal = findPlacementTransform();
    const G4ThreeVector localPt = worldToLocal.TransformPoint(
        G4ThreeVector(Point[0], Point[1], Point[2]));
    const G4double localPos[4] = {localPt.x(), localPt.y(), localPt.z(),
                                  Point[3]};

    getLocalField(localPos, field);

    for (int i = 0; i < nComponents; i += 3) {
      const G4ThreeVector v = worldToLocal.InverseTransformAxis(
          G4ThreeVector(field[i], field[i + 1], field[i + 2]));
      field[i] = v.x();
      field[i + 1] = v.y();
      field[i + 2] = v.z();
    }
  }

private:
  // world-to-local transform of the placement of the field's logical volume
  // that the current navigation history is in
  G4AffineTransform findPlacementTransform() const;

  const G4LogicalVolume *m_logicalVolume;
};

#endif // GateFieldBase_h
