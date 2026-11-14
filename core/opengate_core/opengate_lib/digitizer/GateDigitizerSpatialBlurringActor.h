/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerSpatialBlurringActor_h
#define GateDigitizerSpatialBlurringActor_h

#include "../GateUniqueVolumeID.h"
#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <G4LogicalVolume.hh>
#include <G4VSolid.hh>
#include <map>
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Digitizer module for blurring a (global) spatial position.
 *
 * The blurring is a Gaussian, applied independently along the three axes of
 * the "limits volume" (by default the volume the actor is attached to). The
 * edge policy defines what happens near the limits (bounding box) of this
 * volume:
 * - none: plain Gaussian, the position may end up outside the volume;
 * - clamp: positions outside are moved onto the boundary;
 * - truncated: truncated Gaussian (same sigma, redrawn inside the limits);
 * - truncated_std: truncated Gaussian whose width is increased so that the
 *   rms distance between the blurred and the true positions is the requested
 *   sigma (when possible).
 */

class GateDigitizerSpatialBlurringActor : public GateVDigitizerWithOutputActor {

public:
  enum class EdgePolicy { None, Clamp, Truncated, TruncatedStd };

  // constructor
  explicit GateDigitizerSpatialBlurringActor(py::dict &user_info);

  // destructor
  ~GateDigitizerSpatialBlurringActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  // Blur one coordinate
  static double BlurOneCoordinate(EdgePolicy policy, double mu, double sigma,
                                  double low, double high);

  // Width of the parent Gaussian such that the truncated Gaussian on
  // [low, high], centred on mu, has a rms distance to mu equal to sigma.
  static double ComputeParentSigmaForRms(double mu, double sigma, double low,
                                         double high);

  // Rms distance to mu of the Gaussian (mu, sigma) truncated to [low, high]
  static double ComputeTruncatedRms(double mu, double sigma, double low,
                                    double high);

  // Standard deviation of the Gaussian (mu, sigma) truncated to [low, high]
  // (these three are also available from Python)
  static double ComputeTruncatedStd(double mu, double sigma, double low,
                                    double high);

  static EdgePolicy StringToEdgePolicy(const std::string &s);

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  void BlurCurrentThreeVectorValue();

  // Sample the Gaussian (mu, sigma) truncated to [low, high], mu in [low,
  // high]
  static double SampleTruncatedGaussian(double mu, double sigma, double low,
                                        double high);

  static double pdf(double x);
  static double cdf(double x);
  static double inverse_cdf(double p);

  std::string fBlurAttributeName;
  G4ThreeVector fBlurSigma3;
  EdgePolicy fEdgePolicy;
  std::string fLimitsVolumeName;
  GateVDigiAttribute *fOutputBlurAttribute{};

  struct Extent {
    G4ThreeVector fMin;
    G4ThreeVector fMax;
  };

  // During computation (thread local)
  struct threadLocalT {
    GateUniqueVolumeID::Pointer *fVolumeId;
    G4ThreeVector *fAtt3Value{};
    const G4LogicalVolume *fLimitsLogicalVolume = nullptr;
    // bounding box of each solid, computed once
    std::map<const G4VSolid *, Extent> fExtents;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerSpatialBlurringActor_h
