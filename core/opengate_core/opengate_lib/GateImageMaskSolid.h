/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateImageMaskSolid_h
#define GateImageMaskSolid_h

#include <G4ThreeVector.hh>
#include <G4VSolid.hh>
#include <array>
#include <vector>

/*
  The solid of an image volume with an "outside": the union of the
  "inside" voxels of a regular grid (a staircase), not the box of the
  image. The grid is centred at 0, as the box of an image volume: the
  voxel (i, j, k) spans [-H + i s, -H + (i + 1) s] on each axis (H the
  half size of the box, s the spacing).

  Data (read only after SetMask, shared by the threads):
  - the mask, one byte per voxel, x fastest (as the itk buffer), 1 = inside
  - the distance map: for each outside voxel, a lower bound of the
    distance from any point of the voxel to the inside region (mm); 0 for
    the inside voxels. Computed in Python.

  Tolerance: a point is on the surface (kSurface) if the voxels within
  kCarTolerance/2 of it are not all inside nor all outside (the voxels
  beyond the box are outside). Inside, SurfaceNormal, DistanceToIn and
  DistanceToOut use the same rule.

  It is the container of the voxels of the regular navigation
  (G4PhantomParameterisation): G4RegularNavigation calls Inside() at each
  voxel crossing, the world level calls DistanceToIn.
*/

class GateImageMaskSolid : public G4VSolid {
public:
  explicit GateImageMaskSolid(const G4String &name);
  ~GateImageMaskSolid() override = default;
  GateImageMaskSolid(const GateImageMaskSolid &) = default;

  // size (nx, ny, nz), spacing (mm), mask and distance map: x fastest
  void SetMask(const std::array<int, 3> &size,
               const std::array<double, 3> &spacing,
               const std::vector<unsigned char> &mask,
               const std::vector<float> &distance);

  EInside Inside(const G4ThreeVector &p) const override;
  G4ThreeVector SurfaceNormal(const G4ThreeVector &p) const override;
  G4double DistanceToIn(const G4ThreeVector &p,
                        const G4ThreeVector &v) const override;
  G4double DistanceToIn(const G4ThreeVector &p) const override;
  G4double DistanceToOut(const G4ThreeVector &p, const G4ThreeVector &v,
                         const G4bool calcNorm = false,
                         G4bool *validNorm = nullptr,
                         G4ThreeVector *n = nullptr) const override;
  G4double DistanceToOut(const G4ThreeVector &p) const override;

  void BoundingLimits(G4ThreeVector &pMin, G4ThreeVector &pMax) const override;
  G4bool CalculateExtent(const EAxis pAxis, const G4VoxelLimits &pVoxelLimit,
                         const G4AffineTransform &pTransform, G4double &pMin,
                         G4double &pMax) const override;

  G4double GetCubicVolume() override;
  G4double GetSurfaceArea() override;
  G4ThreeVector GetPointOnSurface() const override;

  G4GeometryType GetEntityType() const override;
  G4VSolid *Clone() const override;
  std::ostream &StreamInfo(std::ostream &os) const override;

  void DescribeYourselfTo(G4VGraphicsScene &scene) const override;
  G4Polyhedron *CreatePolyhedron() const override;

  // for the tests
  bool IsVoxelInside(int i, int j, int k) const { return In(i, j, k); }
  std::size_t GetNumberOfInsideVoxels() const { return fNbInside; }
  std::size_t GetNumberOfSurfaceFaces() const { return fFaces.size(); }

protected:
  std::array<int, 3> fSize{};
  std::array<double, 3> fSpacing{};
  std::array<double, 3> fHalf{};
  std::vector<unsigned char> fMask;
  std::vector<float> fDistance;
  double fHalfTol;
  double fMaxSpacing = 0;
  std::size_t fNbInside = 0;

  // the faces between an inside and an outside voxel (for
  // GetPointOnSurface and GetSurfaceArea): the inside voxel, the axis, the
  // side (+1 / -1), and the cumulated area
  struct Face {
    int i, j, k;
    int axis;
    int side;
  };
  std::vector<Face> fFaces;
  std::vector<double> fFacesCumulatedArea;
  double fSurfaceArea = 0;

  bool In(int i, int j, int k) const {
    if (i < 0 || j < 0 || k < 0 || i >= fSize[0] || j >= fSize[1] ||
        k >= fSize[2])
      return false;
    return fMask[Index(i, j, k)] != 0;
  }
  std::size_t Index(int i, int j, int k) const {
    return std::size_t(i) +
           std::size_t(fSize[0]) * (std::size_t(j) + std::size_t(fSize[1]) * k);
  }
  // position of the lower face of the voxel i along the axis a
  double Plane(int a, int i) const { return -fHalf[a] + i * fSpacing[a]; }

  // the voxel indices within kCarTolerance/2 of x along the axis a: one
  // or two (lo, hi = lo or lo + 1); returns false if x is beyond the box
  // by more than the tolerance
  bool Candidates(int a, double x, int &lo, int &hi) const;

  // the voxel index along the axis a of the point x, for a ray of
  // direction component d: at a face, the voxel ahead (d != 0); with
  // d == 0 at a face, both (lo, hi)
  void AheadIndex(int a, double x, double d, int &lo, int &hi) const;

  // all the voxels of the cell [lo, hi] are inside / at least one is
  bool AllIn(const int lo[3], const int hi[3]) const;
  bool AnyIn(const int lo[3], const int hi[3]) const;

  // the distance from p (in the voxel v) to the nearest voxel of the 3x3x3
  // neighbourhood that is inside (wantInside) or outside, bounded by the
  // distance to the border of the neighbourhood
  double LocalDistance(const G4ThreeVector &p, const int v[3],
                       bool wantInside) const;

  // the ray march (3D DDA) from p + t0 v: the first time the ray enters
  // the region (toInside: an inside cell; otherwise an outside cell); with
  // the exit normal for toInside == false
  double March(const G4ThreeVector &p, const G4ThreeVector &v, double t0,
               double tEnd, bool toInside, G4ThreeVector *normal) const;

  // the outward normal at p (on the surface) for a ray leaving along v
  G4ThreeVector ExitNormal(const G4ThreeVector &p,
                           const G4ThreeVector &v) const;

  // ray / box (slabs), false if no intersection
  bool RayBox(const G4ThreeVector &p, const G4ThreeVector &v, double &t0,
              double &t1) const;

  void BuildFaces();
};

#endif // GateImageMaskSolid_h
