/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateImageMaskSolid.h"
#include <G4AffineTransform.hh>
#include <G4BoundingEnvelope.hh>
#include <G4Polyhedron.hh>
#include <G4VGraphicsScene.hh>
#include <G4VoxelLimits.hh>
#include <Randomize.hh>
#include <algorithm>
#include <cmath>
#include <limits>
#include <sstream>

GateImageMaskSolid::GateImageMaskSolid(const G4String &name) : G4VSolid(name) {
  fHalfTol = 0.5 * kCarTolerance;
}

void GateImageMaskSolid::SetMask(const std::array<int, 3> &size,
                                 const std::array<double, 3> &spacing,
                                 const std::vector<unsigned char> &mask,
                                 const std::vector<float> &distance) {
  const std::size_t n = std::size_t(size[0]) * size[1] * size[2];
  if (size[0] <= 0 || size[1] <= 0 || size[2] <= 0 || mask.size() != n ||
      distance.size() != n) {
    std::ostringstream oss;
    oss << "GateImageMaskSolid " << GetName()
        << ": the mask or the distance map does not match the size";
    G4Exception("GateImageMaskSolid::SetMask", "GateImageMask0001",
                FatalException, oss.str().c_str());
  }
  fSize = size;
  fSpacing = spacing;
  fMaxSpacing = 0;
  for (int a = 0; a < 3; a++) {
    fHalf[a] = 0.5 * size[a] * spacing[a];
    fMaxSpacing = std::max(fMaxSpacing, spacing[a]);
  }
  fMask = mask;
  fDistance = distance;
  fNbInside = 0;
  for (std::size_t i = 0; i < n; i++) {
    if (fMask[i] != 0) {
      fMask[i] = 1;
      fDistance[i] = 0;
      fNbInside++;
    } else if (!(fDistance[i] > 0))
      fDistance[i] = 0; // also NaN
  }
  BuildFaces();
}

void GateImageMaskSolid::BuildFaces() {
  fFaces.clear();
  fFacesCumulatedArea.clear();
  fSurfaceArea = 0;
  for (int k = 0; k < fSize[2]; k++)
    for (int j = 0; j < fSize[1]; j++)
      for (int i = 0; i < fSize[0]; i++) {
        if (!In(i, j, k))
          continue;
        const int v[3] = {i, j, k};
        for (int a = 0; a < 3; a++) {
          const double area = fSpacing[(a + 1) % 3] * fSpacing[(a + 2) % 3];
          for (int side = -1; side <= 1; side += 2) {
            int w[3] = {v[0], v[1], v[2]};
            w[a] += side;
            if (In(w[0], w[1], w[2]))
              continue;
            fFaces.push_back({i, j, k, a, side});
            fSurfaceArea += area;
            fFacesCumulatedArea.push_back(fSurfaceArea);
          }
        }
      }
}

//-----------------------------------------------------------------------------
bool GateImageMaskSolid::Candidates(const int a, const double x, int &lo,
                                    int &hi) const {
  if (x < -fHalf[a] - fHalfTol || x > fHalf[a] + fHalfTol)
    return false;
  const int i = int(std::floor((x + fHalf[a]) / fSpacing[a]));
  const double f = x - Plane(a, i);
  if (f < fHalfTol) {
    lo = i - 1;
    hi = i;
  } else if (fSpacing[a] - f < fHalfTol) {
    lo = i;
    hi = i + 1;
  } else {
    lo = hi = i;
  }
  return true;
}

void GateImageMaskSolid::AheadIndex(const int a, const double x, const double d,
                                    int &lo, int &hi) const {
  const int i = int(std::floor((x + fHalf[a]) / fSpacing[a]));
  const double f = x - Plane(a, i);
  int b; // the index of the plane the point is on
  if (f < fHalfTol)
    b = i;
  else if (fSpacing[a] - f < fHalfTol)
    b = i + 1;
  else {
    lo = hi = i;
    return;
  }
  if (d > 0)
    lo = hi = b;
  else if (d < 0)
    lo = hi = b - 1;
  else {
    lo = b - 1;
    hi = b;
  }
}

bool GateImageMaskSolid::AllIn(const int lo[3], const int hi[3]) const {
  for (int k = lo[2]; k <= hi[2]; k++)
    for (int j = lo[1]; j <= hi[1]; j++)
      for (int i = lo[0]; i <= hi[0]; i++)
        if (!In(i, j, k))
          return false;
  return true;
}

bool GateImageMaskSolid::AnyIn(const int lo[3], const int hi[3]) const {
  for (int k = lo[2]; k <= hi[2]; k++)
    for (int j = lo[1]; j <= hi[1]; j++)
      for (int i = lo[0]; i <= hi[0]; i++)
        if (In(i, j, k))
          return true;
  return false;
}

//-----------------------------------------------------------------------------
EInside GateImageMaskSolid::Inside(const G4ThreeVector &p) const {
  int lo[3], hi[3];
  for (int a = 0; a < 3; a++)
    if (!Candidates(a, p[a], lo[a], hi[a]))
      return kOutside;
  int nin = 0, nout = 0;
  for (int k = lo[2]; k <= hi[2]; k++)
    for (int j = lo[1]; j <= hi[1]; j++)
      for (int i = lo[0]; i <= hi[0]; i++)
        In(i, j, k) ? nin++ : nout++;
  if (nout == 0)
    return kInside;
  if (nin == 0)
    return kOutside;
  return kSurface;
}

//-----------------------------------------------------------------------------
G4ThreeVector GateImageMaskSolid::SurfaceNormal(const G4ThreeVector &p) const {
  int lo[3], hi[3];
  bool ok = true;
  for (int a = 0; a < 3; a++)
    ok = ok && Candidates(a, p[a], lo[a], hi[a]);
  G4ThreeVector n(0, 0, 0);
  if (ok) {
    for (int a = 0; a < 3; a++) {
      if (lo[a] == hi[a])
        continue;
      const int b = (a + 1) % 3, c = (a + 2) % 3;
      bool plus = false, minus = false;
      for (int ib = lo[b]; ib <= hi[b]; ib++)
        for (int ic = lo[c]; ic <= hi[c]; ic++) {
          int v0[3], v1[3];
          v0[a] = lo[a];
          v1[a] = hi[a];
          v0[b] = v1[b] = ib;
          v0[c] = v1[c] = ic;
          const bool in0 = In(v0[0], v0[1], v0[2]);
          const bool in1 = In(v1[0], v1[1], v1[2]);
          if (in0 && !in1)
            plus = true;
          if (!in0 && in1)
            minus = true;
        }
      if (plus != minus)
        n[a] = plus ? 1.0 : -1.0;
    }
  }
  if (n.mag2() > 0)
    return n.unit();

  // not on a face: the nearest in/out face of the voxel of p
  int v[3];
  for (int a = 0; a < 3; a++) {
    const double x = std::clamp(p[a], -fHalf[a], fHalf[a]);
    v[a] = std::clamp(int(std::floor((x + fHalf[a]) / fSpacing[a])), 0,
                      fSize[a] - 1);
  }
  const bool inV = In(v[0], v[1], v[2]);
  double best = kInfinity;
  for (int a = 0; a < 3; a++)
    for (int side = -1; side <= 1; side += 2) {
      int w[3] = {v[0], v[1], v[2]};
      w[a] += side;
      if (In(w[0], w[1], w[2]) == inV)
        continue;
      const double plane = side > 0 ? Plane(a, v[a] + 1) : Plane(a, v[a]);
      const double d = std::fabs(p[a] - plane);
      if (d < best) {
        best = d;
        n = G4ThreeVector(0, 0, 0);
        n[a] = inV ? side : -side;
      }
    }
  if (n.mag2() > 0)
    return n;
  // no in/out face around: the nearest face of the box
  best = kInfinity;
  for (int a = 0; a < 3; a++) {
    const double d = fHalf[a] - std::fabs(p[a]);
    if (d < best) {
      best = d;
      n = G4ThreeVector(0, 0, 0);
      n[a] = p[a] >= 0 ? 1.0 : -1.0;
    }
  }
  return n;
}

G4ThreeVector GateImageMaskSolid::ExitNormal(const G4ThreeVector &p,
                                             const G4ThreeVector &v) const {
  // the ray leaves at p into the cell ahead (outside): the faces it crosses
  // from an inside voxel, i.e. the axes a for which the cell just behind
  // along a has an inside voxel. If none (through an edge or a corner from
  // a diagonal voxel): all the axes whose plane the point is on.
  int lo[3], hi[3];
  bool onPlane[3];
  for (int a = 0; a < 3; a++) {
    AheadIndex(a, p[a], v[a], lo[a], hi[a]);
    int l, h;
    Candidates(a, p[a], l, h);
    onPlane[a] = (l != h);
  }
  G4ThreeVector n(0, 0, 0);
  for (int a = 0; a < 3; a++) {
    if (v[a] == 0 || !onPlane[a])
      continue;
    const int step = v[a] > 0 ? 1 : -1;
    int blo[3] = {lo[0], lo[1], lo[2]};
    int bhi[3] = {hi[0], hi[1], hi[2]};
    blo[a] -= step;
    bhi[a] -= step;
    if (AnyIn(blo, bhi))
      n[a] = step;
  }
  if (n.mag2() == 0)
    for (int a = 0; a < 3; a++)
      if (v[a] != 0 && onPlane[a])
        n[a] = v[a] > 0 ? 1 : -1;
  if (n.mag2() == 0)
    return SurfaceNormal(p);
  return n.unit();
}

//-----------------------------------------------------------------------------
double GateImageMaskSolid::LocalDistance(const G4ThreeVector &p, const int v[3],
                                         const bool wantInside) const {
  // bounded by the border of the 3x3x3 neighbourhood
  double best = kInfinity;
  for (int a = 0; a < 3; a++) {
    best = std::min(best, p[a] - Plane(a, v[a] - 1));
    best = std::min(best, Plane(a, v[a] + 2) - p[a]);
  }
  double best2 = best * best;
  for (int dk = -1; dk <= 1; dk++)
    for (int dj = -1; dj <= 1; dj++)
      for (int di = -1; di <= 1; di++) {
        const int w[3] = {v[0] + di, v[1] + dj, v[2] + dk};
        if (In(w[0], w[1], w[2]) != wantInside)
          continue;
        double d2 = 0;
        for (int a = 0; a < 3; a++) {
          const double l = Plane(a, w[a]);
          const double h = Plane(a, w[a] + 1);
          const double e = std::max({l - p[a], 0.0, p[a] - h});
          d2 += e * e;
        }
        best2 = std::min(best2, d2);
      }
  return std::sqrt(best2);
}

G4double GateImageMaskSolid::DistanceToIn(const G4ThreeVector &p) const {
  if (Inside(p) != kOutside)
    return 0;
  // the voxel of p (or of its projection on the box)
  int v[3];
  G4ThreeVector q;
  for (int a = 0; a < 3; a++) {
    q[a] = std::clamp(p[a], -fHalf[a], fHalf[a]);
    v[a] = std::clamp(int(std::floor((q[a] + fHalf[a]) / fSpacing[a])), 0,
                      fSize[a] - 1);
  }
  const double dbox = (p - q).mag();
  double d = fDistance[Index(v[0], v[1], v[2])];
  if (dbox > 0)
    return std::max(dbox, d - dbox);
  if (d < 2 * fMaxSpacing)
    d = std::max(d, LocalDistance(p, v, true));
  return d;
}

G4double GateImageMaskSolid::DistanceToOut(const G4ThreeVector &p) const {
  if (Inside(p) != kInside)
    return 0;
  int v[3];
  for (int a = 0; a < 3; a++)
    v[a] = std::clamp(int(std::floor((p[a] + fHalf[a]) / fSpacing[a])), 0,
                      fSize[a] - 1);
  return LocalDistance(p, v, false);
}

//-----------------------------------------------------------------------------
bool GateImageMaskSolid::RayBox(const G4ThreeVector &p, const G4ThreeVector &v,
                                double &t0, double &t1) const {
  t0 = -kInfinity;
  t1 = kInfinity;
  for (int a = 0; a < 3; a++) {
    if (v[a] == 0) {
      if (p[a] < -fHalf[a] - fHalfTol || p[a] > fHalf[a] + fHalfTol)
        return false;
      continue;
    }
    double ta = (-fHalf[a] - p[a]) / v[a];
    double tb = (fHalf[a] - p[a]) / v[a];
    if (ta > tb)
      std::swap(ta, tb);
    t0 = std::max(t0, ta);
    t1 = std::min(t1, tb);
  }
  return t1 >= t0 && t1 > 0;
}

double GateImageMaskSolid::March(const G4ThreeVector &p, const G4ThreeVector &v,
                                 double t, const double tEnd,
                                 const bool toInside,
                                 G4ThreeVector *normal) const {
  int lo[3], hi[3], step[3];
  double tMax[3], tDelta[3];

  // set the cell and the next plane crossings at p + t v
  auto setup = [&](const double tt) {
    const G4ThreeVector x = p + tt * v;
    for (int a = 0; a < 3; a++) {
      AheadIndex(a, x[a], v[a], lo[a], hi[a]);
      if (v[a] > 0) {
        step[a] = 1;
        tMax[a] = (Plane(a, lo[a] + 1) - p[a]) / v[a];
        tDelta[a] = fSpacing[a] / v[a];
      } else if (v[a] < 0) {
        step[a] = -1;
        tMax[a] = (Plane(a, lo[a]) - p[a]) / v[a];
        tDelta[a] = -fSpacing[a] / v[a];
      } else {
        step[a] = 0;
        tMax[a] = kInfinity;
        tDelta[a] = kInfinity;
      }
    }
  };
  auto outOfRange = [&]() {
    for (int a = 0; a < 3; a++)
      if (hi[a] < 0 || lo[a] >= fSize[a])
        return true;
    return false;
  };

  auto startNormal = [&]() { return ExitNormal(p + t * v, v); };

  setup(t);
  G4ThreeVector lastNormal(0, 0, 0);
  const long maxIter = 4L * (fSize[0] + fSize[1] + fSize[2]) + 100;
  for (long iter = 0; iter < maxIter; iter++) {
    if (outOfRange()) {
      if (toInside)
        return kInfinity;
      if (normal != nullptr)
        *normal = lastNormal.mag2() > 0 ? lastNormal.unit() : startNormal();
      return t;
    }
    if (toInside) {
      if (AllIn(lo, hi))
        return t;
      // jump with the distance map (lower bound for any point of the cell)
      double d = kInfinity;
      for (int k = lo[2]; k <= hi[2]; k++)
        for (int j = lo[1]; j <= hi[1]; j++)
          for (int i = lo[0]; i <= hi[0]; i++)
            if (i >= 0 && j >= 0 && k >= 0 && i < fSize[0] && j < fSize[1] &&
                k < fSize[2])
              d = std::min(d, double(fDistance[Index(i, j, k)]));
      if (d > fMaxSpacing && d < kInfinity) {
        t += d;
        if (t > tEnd)
          return kInfinity;
        setup(t);
        continue;
      }
    } else if (!AnyIn(lo, hi)) {
      if (normal != nullptr)
        *normal = lastNormal.mag2() > 0 ? lastNormal.unit() : startNormal();
      return t;
    }
    // next cell: the axes whose plane is crossed first (all of them
    // within the tolerance: through an edge or a corner)
    double tm = std::min({tMax[0], tMax[1], tMax[2]});
    if (tm >= kInfinity) // no direction (v == 0)
      return toInside ? kInfinity : 0;
    lastNormal = G4ThreeVector(0, 0, 0);
    for (int a = 0; a < 3; a++) {
      if (step[a] != 0 && tMax[a] - tm < fHalfTol) {
        lo[a] += step[a];
        hi[a] += step[a];
        tMax[a] += tDelta[a];
        lastNormal[a] = step[a];
      }
    }
    t = tm;
    if (toInside && t > tEnd + fHalfTol)
      return kInfinity;
  }
  std::ostringstream oss;
  oss << "GateImageMaskSolid " << GetName() << ": ray march stopped, p = " << p
      << " v = " << v;
  G4Exception("GateImageMaskSolid::March", "GateImageMask1001", JustWarning,
              oss.str().c_str());
  return toInside ? kInfinity : t;
}

G4double GateImageMaskSolid::DistanceToIn(const G4ThreeVector &p,
                                          const G4ThreeVector &v) const {
  if (Inside(p) == kInside)
    return 0;
  double t0, t1;
  if (!RayBox(p, v, t0, t1))
    return kInfinity;
  const double t = March(p, v, std::max(t0, 0.0), t1, true, nullptr);
  if (t < fHalfTol)
    return 0;
  return t;
}

G4double GateImageMaskSolid::DistanceToOut(const G4ThreeVector &p,
                                           const G4ThreeVector &v,
                                           const G4bool calcNorm,
                                           G4bool *validNorm,
                                           G4ThreeVector *n) const {
  G4ThreeVector normal;
  double t = 0;
  double t0, t1;
  if (!RayBox(p, v, t0, t1))
    normal = ExitNormal(p, v);
  else {
    t = March(p, v, 0, t1, false, &normal);
    if (t < fHalfTol)
      t = 0;
  }
  if (calcNorm) {
    if (validNorm != nullptr)
      *validNorm = false; // not convex
    if (n != nullptr)
      *n = normal;
  }
  return t;
}

//-----------------------------------------------------------------------------
void GateImageMaskSolid::BoundingLimits(G4ThreeVector &pMin,
                                        G4ThreeVector &pMax) const {
  pMin.set(-fHalf[0], -fHalf[1], -fHalf[2]);
  pMax.set(fHalf[0], fHalf[1], fHalf[2]);
}

G4bool GateImageMaskSolid::CalculateExtent(const EAxis pAxis,
                                           const G4VoxelLimits &pVoxelLimit,
                                           const G4AffineTransform &pTransform,
                                           G4double &pMin,
                                           G4double &pMax) const {
  G4ThreeVector bmin, bmax;
  BoundingLimits(bmin, bmax);
  G4BoundingEnvelope bbox(bmin, bmax);
  return bbox.CalculateExtent(pAxis, pVoxelLimit, pTransform, pMin, pMax);
}

G4double GateImageMaskSolid::GetCubicVolume() {
  return double(fNbInside) * fSpacing[0] * fSpacing[1] * fSpacing[2];
}

G4double GateImageMaskSolid::GetSurfaceArea() { return fSurfaceArea; }

G4ThreeVector GateImageMaskSolid::GetPointOnSurface() const {
  if (fFaces.empty())
    return {0, 0, 0};
  const double u = G4UniformRand() * fSurfaceArea;
  auto it = std::upper_bound(fFacesCumulatedArea.begin(),
                             fFacesCumulatedArea.end(), u);
  std::size_t f = std::min<std::size_t>(it - fFacesCumulatedArea.begin(),
                                        fFaces.size() - 1);
  const auto &face = fFaces[f];
  const int v[3] = {face.i, face.j, face.k};
  G4ThreeVector p;
  for (int a = 0; a < 3; a++) {
    if (a == face.axis)
      p[a] = face.side > 0 ? Plane(a, v[a] + 1) : Plane(a, v[a]);
    else
      p[a] = Plane(a, v[a]) + G4UniformRand() * fSpacing[a];
  }
  return p;
}

G4GeometryType GateImageMaskSolid::GetEntityType() const {
  return {"GateImageMaskSolid"};
}

G4VSolid *GateImageMaskSolid::Clone() const {
  return new GateImageMaskSolid(*this);
}

std::ostream &GateImageMaskSolid::StreamInfo(std::ostream &os) const {
  os << "-----------------------------------------------------------\n"
     << "    *** Dump for solid - " << GetName() << " ***\n"
     << "    ===================================================\n"
     << " Solid type: GateImageMaskSolid\n"
     << " Size: " << fSize[0] << " " << fSize[1] << " " << fSize[2] << "\n"
     << " Spacing (mm): " << fSpacing[0] << " " << fSpacing[1] << " "
     << fSpacing[2] << "\n"
     << " Inside voxels: " << fNbInside << "\n"
     << "-----------------------------------------------------------\n";
  return os;
}

void GateImageMaskSolid::DescribeYourselfTo(G4VGraphicsScene &scene) const {
  scene.AddSolid(*this);
}

G4Polyhedron *GateImageMaskSolid::CreatePolyhedron() const {
  // the box of the image (visualisation only)
  return new G4PolyhedronBox(fHalf[0], fHalf[1], fHalf[2]);
}
