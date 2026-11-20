/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerChargeInductionActor_h
#define GateDigitizerChargeInductionActor_h

#include "GateDigiAttributePolicies.h"
#include "GateVDigitizerWithOutputActor.h"
#include <G4AffineTransform.hh>
#include <G4Cache.hh>
#include <array>
#include <cstdint>
#include <map>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Charge induction and readout by pixel, for a monolithic semiconductor
 * crystal (e.g. CZT) with a pixelated anode.
 *
 * Input: hits. Output: one digi per (event, crystal, pixel).
 *
 * The pixel grid is defined in the local coordinate system of the attached
 * volume (the crystal, a box): number_of_pixels x pixel_size, centred on
 * fGridCenter, in the local XY plane (set from Python, either given by the
 * user or read from a repeated pixel volume). The pixel of a hit comes from
 * its local position, or, if a pixel volume is set, from the copy number of
 * the pixel volume the hit is in (hits that are not in a pixel volume are
 * ignored, see GetIgnoredHitsCount). The depth z of a hit is its distance to
 * the cathode (0 to the thickness of the crystal).
 *
 * For each hit of energy E, at depth z and at (dx, dy) relative to the
 * centre of a pixel (the pixel of the hit and, if neighbours = 1, the 8
 * pixels around):
 *
 *      signal[pixel] += E * eta(z, dx, dy)
 *
 * with eta = eta_own for the pixel of the hit and eta_neighbour for the
 * others (two 3D tables, trilinear interpolation, clamped at the borders).
 * The tables hold all the physics (weighting potential, trapping, charge
 * cloud); they are computed on the Python side.
 *
 * Then: signal x gain, signals below the threshold are dropped. The output
 * digi has:
 * - TotalEnergyDeposit: the signal
 * - PostPosition: centre of the pixel (global; local z = 0)
 * - PostPositionLocal: centre of the pixel (local)
 * - PixelIndexX, PixelIndexY: indices of the pixel
 * - GlobalTime: earliest time of the hits that contribute to the pixel
 * - attributes with a policy (attribute_policies, see
 *   GateDigiAttributePolicies; energy_winner: the hit with the largest
 *   |contribution| to the pixel)
 * - all other attributes: copied from the hit with the largest |contribution|
 *
 * Grouping is per event, per volume (UniqueVolumeID up to the depth of the
 * crystal) and per weight (VRT), as the adder.
 */

class GateDigitizerChargeInductionActor : public GateVDigitizerWithOutputActor {

public:
  explicit GateDigitizerChargeInductionActor(py::dict &user_info);

  ~GateDigitizerChargeInductionActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  // Called when the simulation starts (master thread only)
  void StartSimulationAction() override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  // Called by every worker when the simulation is about to end
  void EndOfSimulationWorkerAction(const G4Run *lastRun) override;

  // Depth of the crystal volume in the geometrical tree
  void SetCrystalDepth(int depth);

  // Thickness of the crystal along the local Z axis
  void SetCrystalThickness(double t);

  // Pixel grid in the local XY plane of the crystal: size of a pixel, number
  // of pixels, centre of the grid
  void SetGrid(const std::vector<double> &pixel_size,
               const std::vector<int> &number_of_pixels,
               const std::vector<double> &center);

  // Repeated pixel volume (daughter of the crystal): its depth and, for each
  // copy number, the indices of the pixel
  void SetPixelVolume(int depth, const std::vector<int> &copy_to_ix,
                      const std::vector<int> &copy_to_iy);

  // Tables of the induced charge (shape nz, nx, ny, C order), the position of
  // the first node and the spacing (z, x, y). z: distance to the cathode;
  // x, y: position of the hit relative to the centre of the pixel.
  void SetTables(
      const py::array_t<double, py::array::c_style | py::array::forcecast> &own,
      const py::array_t<double, py::array::c_style | py::array::forcecast>
          &neighbour,
      const std::vector<double> &origin, const std::vector<double> &spacing);

  // Optional separable cloud term: 1D tables (values, first node, spacing)
  // along x, y (share of the cloud on the pad) and z (share of the electrons
  // that reach the anode). eta += (fx(dx) fy(dy) - own) fz(z)
  void SetCloudTables(const std::vector<double> &fx, double x0, double dx,
                      const std::vector<double> &fy, double y0, double dy,
                      const std::vector<double> &fz, double z0, double dz);

  // Value of a table at (z, dx, dy) (for tests)
  double GetEta(bool own, double z, double dx, double dy) const;

  unsigned long GetIgnoredHitsCount() const { return fIgnoredHitsCount; }

protected:
  struct PixelKey {
    uint64_t volumeID;
    uint64_t weightBits;
    int pixel;

    bool operator<(const PixelKey &o) const {
      if (volumeID != o.volumeID)
        return volumeID < o.volumeID;
      if (weightBits != o.weightBits)
        return weightBits < o.weightBits;
      return pixel < o.pixel;
    }
  };

  struct PixelSignal {
    double fSignal = 0;
    double fTime = DBL_MAX;
    double fBestScore = -1;
    size_t fBestIndex = 0;
    GateDigiAttributePolicies::Tracker fAttributeTracker;
    int fIx = 0;
    int fIy = 0;
    G4AffineTransform fToGlobal;
  };

  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  void ProcessHit();

  // centre of the pixel i along the axis k (local coordinates)
  double PixelCenter(const int k, const int i) const {
    return fGridCenter[k] + (i + 0.5) * fPixelSize[k] -
           fNumberOfPixels[k] * fPixelSize[k] / 2.0;
  }

  double Interpolate(const std::vector<double> &table, double z, double x,
                     double y) const;

  // eta for the pixel of the hit (own) or a neighbour, at (z, dx, dy)
  double Eta(bool own, double z, double dx, double dy) const;

  struct Table1D {
    std::vector<double> fValues;
    double fOrigin = 0;
    double fSpacing = 1;
    double operator()(double p) const;
  };
  bool fCloudFlag = false;
  Table1D fCloudX, fCloudY, fCloudZ;

  // parameters
  std::array<double, 2> fPixelSize{};
  std::array<int, 2> fNumberOfPixels{};
  std::array<double, 2> fGridCenter{};
  int fPixelDepth;
  std::vector<int> fCopyToIx;
  std::vector<int> fCopyToIy;
  bool fCathodeIsPlusZ;
  int fNeighbours;
  double fGain;
  double fThreshold;
  bool fMiddlePositionFlag;
  int fCrystalDepth;
  double fThickness;
  bool fWeightsAreUsedFlag;
  bool fAddPostPositionLocal;
  unsigned long fIgnoredHitsCount;
  GateDigiAttributePolicies fAttributePolicies;

  // tables (read-only during the run, shared by all threads)
  std::vector<double> fEtaOwn;
  std::vector<double> fEtaNeighbour;
  std::array<int, 3> fTableShape{};
  std::array<double, 3> fTableOrigin{};
  std::array<double, 3> fTableSpacing{};

  // output attributes
  GateVDigiAttribute *fOutputEdepAttribute{};
  GateVDigiAttribute *fOutputPosAttribute{};
  GateVDigiAttribute *fOutputLocalPosAttribute{};
  GateVDigiAttribute *fOutputGlobalTimeAttribute{};
  GateVDigiAttribute *fOutputPixelIndexXAttribute{};
  GateVDigiAttribute *fOutputPixelIndexYAttribute{};

  // thread local
  struct threadLocalT {
    std::map<PixelKey, PixelSignal> fPixels;
    double *edep{};
    G4ThreeVector *pos{};
    G4ThreeVector *prePos{};
    GateUniqueVolumeID::Pointer *volID{};
    double *time{};
    double *weight{};
    unsigned long fIgnoredHitsCount = 0;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerChargeInductionActor_h
