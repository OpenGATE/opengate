/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerSpatialBlurringActor.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include <G4LogicalVolumeStore.hh>
#include <G4VoxelLimits.hh>
#include <Randomize.hh>
#include <algorithm>
#include <cmath>

namespace {
constexpr double kInvSqrt2Pi = 0.39894228040143267794; // 1/sqrt(2 pi)
constexpr double kInvSqrt2 = 0.70710678118654752440;   // 1/sqrt(2)
} // namespace

GateDigitizerSpatialBlurringActor::GateDigitizerSpatialBlurringActor(
    py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {
  // actions
  fActions.insert("EndOfEventAction");
  fEdgePolicy = EdgePolicy::Truncated;
}

GateDigitizerSpatialBlurringActor::~GateDigitizerSpatialBlurringActor() =
    default;

GateDigitizerSpatialBlurringActor::EdgePolicy
GateDigitizerSpatialBlurringActor::StringToEdgePolicy(const std::string &s) {
  if (s == "none")
    return EdgePolicy::None;
  if (s == "clamp")
    return EdgePolicy::Clamp;
  if (s == "truncated")
    return EdgePolicy::Truncated;
  if (s == "truncated_std")
    return EdgePolicy::TruncatedStd;
  std::ostringstream oss;
  oss << "Error in GateDigitizerSpatialBlurringActor: unknown edge_policy '"
      << s << "'. Must be none, clamp, truncated or truncated_std.";
  Fatal(oss.str());
  return EdgePolicy::None;
}

void GateDigitizerSpatialBlurringActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  fBlurAttributeName = DictGetStr(user_info, "blur_attribute");
  fBlurSigma3 = DictGetG4ThreeVector(user_info, "blur_sigma");
  fEdgePolicy = StringToEdgePolicy(DictGetStr(user_info, "edge_policy"));
  fLimitsVolumeName = DictGetStr(user_info, "limits_volume");
}

void GateDigitizerSpatialBlurringActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  auto a = attributes_not_in_filler;
  a.push_back(fBlurAttributeName);
  GateVDigitizerWithOutputActor::DigitInitialize(a);

  // The unique vol id is required to compute the transform of the volume
  CheckRequiredAttribute(fInputDigiCollection, "PreStepUniqueVolumeID");

  // set output pointers to the attributes needed for computation
  fOutputBlurAttribute =
      fOutputDigiCollection->GetDigiAttribute(fBlurAttributeName);

  // set input pointers to the attributes needed for computation
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  lr.fInputIter.TrackAttribute(fBlurAttributeName, &l.fAtt3Value);
  lr.fInputIter.TrackAttribute("PreStepUniqueVolumeID", &l.fVolumeId);
}

void GateDigitizerSpatialBlurringActor::BeginOfRunAction(const G4Run *run) {
  GateVDigitizerWithOutputActor::BeginOfRunAction(run);
  auto &l = fThreadLocalData.Get();
  // the geometry may change between runs: find the volume again
  l.fLimitsLogicalVolume =
      G4LogicalVolumeStore::GetInstance()->GetVolume(fLimitsVolumeName, false);
  if (l.fLimitsLogicalVolume == nullptr) {
    std::ostringstream oss;
    oss << "Error in the spatial blurring actor '" << GetName()
        << "': cannot find the limits volume '" << fLimitsVolumeName << "'.";
    Fatal(oss.str());
  }
  l.fExtents.clear();
}

void GateDigitizerSpatialBlurringActor::EndOfEventAction(
    const G4Event * /*unused*/) {
  // loop on all digi of this event
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &iter = lr.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    // blur the current value
    BlurCurrentThreeVectorValue();
    // copy the other attributes
    const auto &i = lr.fInputIter.fIndex;
    lr.fDigiAttributeFiller->Fill(i);
    iter++;
  }
}

void GateDigitizerSpatialBlurringActor::BlurCurrentThreeVectorValue() {
  auto &l = fThreadLocalData.Get();
  const auto &position = *l.fAtt3Value;
  const auto &history = (*l.fVolumeId)->fTouchable;

  // Level of the limits volume in the history of the volume where the digi
  // is: the deepest level whose logical volume is the limits volume (this
  // also gives the right copy when the volume is repeated). If it is not
  // found, the volume of the digi itself is used.
  auto depth = static_cast<G4int>(history.GetDepth());
  for (auto d = depth; d >= 0; d--) {
    const auto *pv = history.GetVolume(d);
    if (pv != nullptr && pv->GetLogicalVolume() == l.fLimitsLogicalVolume) {
      depth = d;
      break;
    }
  }

  // position in the coordinate system of the limits volume
  const auto &transform = history.GetTransform(depth);
  const auto local = transform.TransformPoint(position);

  // bounding box of the solid of the limits volume (computed once per solid)
  const auto *solid = history.GetVolume(depth)->GetLogicalVolume()->GetSolid();
  auto it = l.fExtents.find(solid);
  if (it == l.fExtents.end()) {
    const G4VoxelLimits limits;
    const G4AffineTransform at;
    Extent e;
    G4double min, max;
    solid->CalculateExtent(kXAxis, limits, at, min, max);
    e.fMin.setX(min);
    e.fMax.setX(max);
    solid->CalculateExtent(kYAxis, limits, at, min, max);
    e.fMin.setY(min);
    e.fMax.setY(max);
    solid->CalculateExtent(kZAxis, limits, at, min, max);
    e.fMin.setZ(min);
    e.fMax.setZ(max);
    it = l.fExtents.emplace(solid, e).first;
  }
  const auto &e = it->second;

  G4ThreeVector p;
  for (int i = 0; i < 3; i++) {
    p[i] = BlurOneCoordinate(fEdgePolicy, local[i], fBlurSigma3[i], e.fMin[i],
                             e.fMax[i]);
  }

  // convert back the point to the world coordinate system and store
  fOutputBlurAttribute->Fill3Value(transform.InverseTransformPoint(p));
}

double GateDigitizerSpatialBlurringActor::BlurOneCoordinate(
    const EdgePolicy policy, double mu, const double sigma, const double low,
    const double high) {
  if (sigma <= 0)
    return mu;
  if (policy == EdgePolicy::None)
    return G4RandGauss::shoot(mu, sigma);
  if (policy == EdgePolicy::Clamp) {
    static const double tiny = 1 * CLHEP::nm;
    const double x = G4RandGauss::shoot(mu, sigma);
    if (x < low)
      return low + tiny;
    if (x > high)
      return high - tiny;
    return x;
  }
  // truncated policies: the true position should be inside the limits, but
  // it may be very slightly outside (e.g. a PostPosition on the boundary)
  mu = std::clamp(mu, low, high);
  if (policy == EdgePolicy::Truncated)
    return SampleTruncatedGaussian(mu, sigma, low, high);
  // TruncatedStd
  const double s = ComputeParentSigmaForRms(mu, sigma, low, high);
  return SampleTruncatedGaussian(mu, s, low, high);
}

double GateDigitizerSpatialBlurringActor::SampleTruncatedGaussian(
    const double mu, const double sigma, const double low, const double high) {
  const double a = (low - mu) / sigma;
  const double b = (high - mu) / sigma;
  const double Fa = cdf(a);
  const double Fb = cdf(b);
  if (Fb - Fa > 0.3) {
    // rejection: exact, and fast when most of the Gaussian is inside
    while (true) {
      const double x = G4RandGauss::shoot(mu, sigma);
      if (x >= low && x <= high)
        return x;
    }
  }
  // inverse transform sampling: exact, also when only a small part of the
  // Gaussian is inside (mu is inside, so a <= 0 <= b: no extreme tails)
  const double u = Fa + G4UniformRand() * (Fb - Fa);
  const double x = mu + sigma * inverse_cdf(u);
  return std::clamp(x, low, high);
}

double GateDigitizerSpatialBlurringActor::ComputeTruncatedStd(
    const double mu, const double sigma, const double low, const double high) {
  const double a = (low - mu) / sigma;
  const double b = (high - mu) / sigma;
  const double Z = cdf(b) - cdf(a);
  if (Z <= 0)
    return 0;
  const double pa = pdf(a);
  const double pb = pdf(b);
  const double m = (pa - pb) / Z;
  const double v = 1 + (a * pa - b * pb) / Z - m * m;
  return sigma * std::sqrt(std::max(v, 0.0));
}

double GateDigitizerSpatialBlurringActor::ComputeTruncatedRms(
    const double mu, const double sigma, const double low, const double high) {
  // root mean square distance to mu: E[(x - mu)^2] = var + (mean - mu)^2
  const double a = (low - mu) / sigma;
  const double b = (high - mu) / sigma;
  const double Z = cdf(b) - cdf(a);
  if (Z <= 0)
    return 0;
  const double v = 1 + (a * pdf(a) - b * pdf(b)) / Z;
  return sigma * std::sqrt(std::max(v, 0.0));
}

double GateDigitizerSpatialBlurringActor::ComputeParentSigmaForRms(
    const double mu, const double sigma, const double low, const double high) {
  // Far from both edges, the truncation has no effect
  if (mu - low > 6 * sigma && high - mu > 6 * sigma)
    return sigma;
  // The rms distance increases with the parent width, up to the one of the
  // uniform distribution on [low, high] (infinite width). If sigma is larger
  // than that, it cannot be reached: use a very large width (almost uniform).
  const double max_width = 1e3 * std::max(sigma, high - low);
  if (ComputeTruncatedRms(mu, max_width, low, high) <= sigma)
    return max_width;
  // bisection on the parent width
  double s_low = sigma;
  double s_high = 2 * sigma;
  while (ComputeTruncatedRms(mu, s_high, low, high) < sigma)
    s_high *= 2;
  for (int i = 0; i < 60; i++) {
    const double s = 0.5 * (s_low + s_high);
    if (ComputeTruncatedRms(mu, s, low, high) < sigma)
      s_low = s;
    else
      s_high = s;
    if (s_high - s_low < 1e-6 * sigma)
      break;
  }
  return 0.5 * (s_low + s_high);
}

// Standard normal PDF
double GateDigitizerSpatialBlurringActor::pdf(const double x) {
  return kInvSqrt2Pi * std::exp(-0.5 * x * x);
}

// Standard normal CDF
double GateDigitizerSpatialBlurringActor::cdf(const double x) {
  return 0.5 * std::erfc(-x * kInvSqrt2);
}

// Inverse of the standard normal CDF: rational approximation of P. J. Acklam
// (relative error < 1.2e-9), refined by one step of Halley's method.
double GateDigitizerSpatialBlurringActor::inverse_cdf(const double p) {
  if (p <= 0)
    return -HUGE_VAL;
  if (p >= 1)
    return HUGE_VAL;
  static const double a[] = {-3.969683028665376e+01, 2.209460984245205e+02,
                             -2.759285104469687e+02, 1.383577518672690e+02,
                             -3.066479806614716e+01, 2.506628277459239e+00};
  static const double b[] = {-5.447609879822406e+01, 1.615858368580409e+02,
                             -1.556989798598866e+02, 6.680131188771972e+01,
                             -1.328068155288572e+01};
  static const double c[] = {-7.784894002430293e-03, -3.223964580411365e-01,
                             -2.400758277161838e+00, -2.549732539343734e+00,
                             4.374664141464968e+00,  2.938163982698783e+00};
  static const double d[] = {7.784695709041462e-03, 3.224671290700398e-01,
                             2.445134137142996e+00, 3.754408661907416e+00};
  constexpr double p_low = 0.02425;
  double x;
  if (p < p_low) {
    const double q = std::sqrt(-2 * std::log(p));
    x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  } else if (p <= 1 - p_low) {
    const double q = p - 0.5;
    const double r = q * q;
    x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) *
        q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  } else {
    const double q = std::sqrt(-2 * std::log(1 - p));
    x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  // one step of Halley's method
  const double e = cdf(x) - p;
  const double u = e / pdf(x);
  x = x - u / (1 + x * u / 2);
  return x;
}
