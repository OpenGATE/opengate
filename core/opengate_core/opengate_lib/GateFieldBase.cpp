/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateFieldBase.h"
#include <G4VSolid.hh>
#include <cmath>
#include <limits>
#include <sstream>
#include <stdexcept>

// constructor
GateFieldBase::GateFieldBase(const G4VSolid *solid,
                             std::vector<G4ThreeVector> translations,
                             std::vector<G4RotationMatrix> rotations,
                             double deltaChordMM)
    : m_solid(solid),
      m_fallbackFatalDistanceMM(
          5.0 * std::sqrt(8.0 * kMaxCurvatureRadiusMM * deltaChordMM)) {
  if (solid == nullptr)
    throw std::invalid_argument("GateFieldBase: solid must not be null");

  if (translations.size() != rotations.size() || translations.empty())
    throw std::invalid_argument("GateFieldBase: translations and rotations "
                                "must be non-empty and have the same size");

  m_transforms.reserve(translations.size());
  for (std::size_t i = 0; i < translations.size(); ++i)
    m_transforms.emplace_back(rotations[i].inverse(), translations[i]);
}

// recache the world-to-local transforms (e.g. after a geometry change between
// runs)
void GateFieldBase::SetTransforms(std::vector<G4ThreeVector> translations,
                                  std::vector<G4RotationMatrix> rotations) {
  if (translations.size() != rotations.size() || translations.empty())
    throw std::invalid_argument(
        "GateFieldBase::SetTransforms: translations and rotations must be "
        "non-empty and have the same size");

  m_transforms.clear();
  m_transforms.reserve(translations.size());
  for (std::size_t i = 0; i < translations.size(); ++i)
    m_transforms.emplace_back(rotations[i].inverse(), translations[i]);
}

// find the local coordinates of worldPoint in the containing placement of the
// field's logical volume
G4ThreeVector GateFieldBase::findContainingPlacement(
    const G4ThreeVector &worldPoint,
    const G4AffineTransform *&outTransform) const {
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

    const double d = m_solid->DistanceToIn(localPoint);
    if (d < minDistToSurface) {
      minDistToSurface = d;
      closestIdx = i;
      closestLocal = localPoint;
    }
  }

  // if the point is outside every placement, check if it's within the
  // fallback-fatal distance which accounts for any reasonable field integrator
  // overshoot due to tolerances. if not, this is very likely a bug in the
  // geometry or field setup -> fatal
  if (minDistToSurface > m_fallbackFatalDistanceMM) {
    std::ostringstream msg;
    msg << "GateFieldBase::findContainingPlacement: world point ("
        << worldPoint.x() << ", " << worldPoint.y() << ", " << worldPoint.z()
        << ") mm is " << minDistToSurface
        << " mm outside every cached placement of the field's solid — "
        << "well beyond any chord-finder overshoot.\n"
        << "  Closest placement: index " << closestIdx << "  (local point "
        << closestLocal.x() << ", " << closestLocal.y() << ", "
        << closestLocal.z() << ").\n"
        << "  Maximum allowed distance before fatal: "
        << m_fallbackFatalDistanceMM << " mm.\n"
        << "  This likely indicates a real bug in the geometry or field "
           "setup.\n";

    G4Exception("GateFieldBase::findContainingPlacement", "GateField0001",
                FatalException, msg.str().c_str());
  }

  outTransform = &m_transforms[closestIdx];
  return closestLocal;
}

// rotate a field vector from local to world coordinates using the given
// transform
G4ThreeVector GateFieldBase::rotateToWorld(const G4ThreeVector &localField,
                                           const G4AffineTransform &transform) {
  return transform.TransformAxis(localField);
}
