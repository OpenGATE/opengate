/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateField.h"

#include "G4VSolid.hh"
#include "globals.hh" // G4Exception

#include <cmath>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <typeinfo>

// constructor
GateField::GateField(const G4VSolid *solid,
                     std::vector<G4ThreeVector> translations,
                     std::vector<G4RotationMatrix> rotations,
                     double deltaChordMM)
    : m_solid(solid),
      m_fallbackFatalDistanceMM(
          5.0 * std::sqrt(8.0 * kMaxCurvatureRadiusMM * deltaChordMM)) {
  // sanity-check the inputs before caching
  if (solid == nullptr)
    throw std::invalid_argument("GateField: solid must not be null");

  if (translations.size() != rotations.size() || translations.empty())
    throw std::invalid_argument("GateField: translations and rotations must be "
                                "non-empty and have the same size");

  // initial cache the world-to-local transforms for every physical placement of
  // the physical volume
  m_transforms.reserve(translations.size());
  for (std::size_t i = 0; i < translations.size(); ++i)
    m_transforms.emplace_back(rotations[i].inverse(), translations[i]);
}

// recache the world-to-local transforms (e.g. after a geometry change between
// runs)
void GateField::SetTransforms(std::vector<G4ThreeVector> translations,
                              std::vector<G4RotationMatrix> rotations) {

  // sanity-check the inputs before caching
  if (translations.size() != rotations.size() || translations.empty())
    throw std::invalid_argument(
        "GateField::SetTransforms: translations and rotations must be "
        "non-empty and have the same size");

  // recache the world-to-local transforms for every physical placement of the
  // logical volume
  m_transforms.clear();
  m_transforms.reserve(translations.size());
  for (std::size_t i = 0; i < translations.size(); ++i)
    m_transforms.emplace_back(rotations[i].inverse(), translations[i]);
}

// find the local coordinates of worldPoint in the containing placement of the
// field's logical volume, and return the transform of that placement.
G4ThreeVector GateField::findContainingPlacement(
    const G4ThreeVector &worldPoint,
    const G4AffineTransform *&outTransform) const {

  // Loop over all placements once:
  //   - return immediately if the point is inside any placement;
  //   - otherwise accumulate the closest surface distance for the fallback.
  // This avoids re-transforming the point in a second pass.
  std::size_t closestIdx = 0;
  double minDistToSurface = std::numeric_limits<double>::infinity();
  G4ThreeVector closestLocal{};

  for (std::size_t i = 0; i < m_transforms.size(); ++i) {
    const auto &tr = m_transforms[i];
    const G4ThreeVector localPoint = tr.InverseTransformPoint(worldPoint);

    if (m_solid->Inside(localPoint) != kOutside) {
      outTransform = &tr;
      return localPoint;
    }

    // Fallback: track the placement whose surface is nearest.
    // DistanceToIn is valid here because Inside() just returned kOutside.
    const double d = m_solid->DistanceToIn(localPoint);
    if (d < minDistToSurface) {
      minDistToSurface = d;
      closestIdx = i;
      closestLocal = localPoint;
    }
  }

  // sanity check: if the closest surface is still too far, this is likely a
  // real bug
  if (minDistToSurface > m_fallbackFatalDistanceMM) {
    std::ostringstream msg;
    msg << "GateField::findContainingPlacement: world point (" << worldPoint.x()
        << ", " << worldPoint.y() << ", " << worldPoint.z() << ") mm is "
        << minDistToSurface
        << " mm outside every cached placement of the field's solid — "
        << "well beyond any chord-finder overshoot.\n"
        << "  Closest placement: index " << closestIdx << "  (local point "
        << closestLocal.x() << ", " << closestLocal.y() << ", "
        << closestLocal.z() << ").\n"
        << " Maximum allowed distance before fatal: "
        << m_fallbackFatalDistanceMM << " mm.\n"
        << " This likely indicates a real bug in the geometry or field setup\n";

    G4Exception("GateField::findContainingPlacement", "GateField0001",
                FatalException, msg.str().c_str());
  }

  outTransform = &m_transforms[closestIdx];

  return closestLocal;
}

// rotate a field vector from local to world coordinates using the given
// transform
G4ThreeVector GateField::rotateToWorld(const G4ThreeVector &localField,
                                       const G4AffineTransform &transform) {
  return transform.TransformAxis(localField);
}
