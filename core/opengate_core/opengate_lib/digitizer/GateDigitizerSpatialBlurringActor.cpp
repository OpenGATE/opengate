/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerSpatialBlurringActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersGeometry.h"
#include "../GateUniqueVolumeIDManager.h"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <G4Navigator.hh>
#include <G4RunManager.hh>
#include <G4VoxelLimits.hh>
#include <Randomize.hh>
#include <iostream>

#define _USE_MATH_DEFINES
#include <cmath>
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

GateDigitizerSpatialBlurringActor::GateDigitizerSpatialBlurringActor(
    py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {
  // actions
  fActions.insert("EndOfEventAction");
  fUseTruncatedGaussian = false;
  fKeepInSolidLimits = false;
}

GateDigitizerSpatialBlurringActor::~GateDigitizerSpatialBlurringActor() =
    default;

void GateDigitizerSpatialBlurringActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  // blurring method
  fBlurAttributeName = DictGetStr(user_info, "blur_attribute");
  fBlurSigma3 = DictGetG4ThreeVector(user_info, "blur_sigma");
  fKeepInSolidLimits = DictGetBool(user_info, "keep_in_solid_limits");
  fUseTruncatedGaussian = DictGetBool(user_info, "use_truncated_Gaussian");
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
  l.fSolidExtentIsUpdated = false;
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
  // Get the current position
  auto &l = fThreadLocalData.Get();
  const auto &position = *l.fAtt3Value;
  const auto vol_uid = *l.fVolumeId;
  const auto *phys_vol = vol_uid->GetTopPhysicalVolume();

  // Compute the position of 'position' (which is in the world volume) in the
  // local volume
  const auto local_position =
      vol_uid->fTouchable.GetTopTransform().TransformPoint(position);
  G4ThreeVector p(
      G4RandGauss::shoot(local_position.getX(), fBlurSigma3.getX()),
      G4RandGauss::shoot(local_position.getY(), fBlurSigma3.getY()),
      G4RandGauss::shoot(local_position.getZ(), fBlurSigma3.getZ()));

  // check limits according to the volume
  if (!l.fSolidExtentIsUpdated) {
    // the extent is computed only once per run.
    const G4VoxelLimits limits;
    const G4AffineTransform at;
    const auto solid = phys_vol->GetLogicalVolume()->GetSolid();
    solid->CalculateExtent(kXAxis, limits, at, l.fXmin, l.fXmax);
    solid->CalculateExtent(kYAxis, limits, at, l.fYmin, l.fYmax);
    solid->CalculateExtent(kZAxis, limits, at, l.fZmin, l.fZmax);
    l.fSolidExtentIsUpdated = true;
  }

  if (fUseTruncatedGaussian) {
    G4double newX(p.getX()), newY(p.getY()), newZ(p.getZ());
    while ((newX > l.fXmax) || (newX < l.fXmin)) {
      const G4double newSigmaX = (ComputeTruncatedGaussianSigma(
          local_position.getX(), fBlurSigma3.getX(), l.fXmin, l.fXmax));
      newX = G4RandGauss::shoot(local_position.getX(), newSigmaX);
      p.setX(newX);
    }
    while ((newY > l.fYmax) || (newY < l.fYmin)) {
      const G4double newSigmaY = (ComputeTruncatedGaussianSigma(
          local_position.getY(), fBlurSigma3.getY(), l.fYmin, l.fYmax));
      newY = G4RandGauss::shoot(local_position.getY(), newSigmaY);
      p.setY(newY);
    }
    while ((newZ > l.fZmax) || (newZ < l.fZmin)) {
      const G4double newSigmaZ = (ComputeTruncatedGaussianSigma(
          local_position.getZ(), fBlurSigma3.getZ(), l.fZmin, l.fZmax));
      newZ = G4RandGauss::shoot(local_position.getZ(), newSigmaZ);
      p.setZ(newZ);
    }
  } else {
    if (fKeepInSolidLimits) {
      static const double tiny = 1 * CLHEP::nm;
      if (p.getX() < l.fXmin)
        p.setX(l.fXmin + tiny);
      if (p.getY() < l.fYmin)
        p.setY(l.fYmin + tiny);
      if (p.getZ() < l.fZmin)
        p.setZ(l.fZmin + tiny);
      if (p.getX() > l.fXmax)
        p.setX(l.fXmax - tiny);
      if (p.getY() > l.fYmax)
        p.setY(l.fYmax - tiny);
      if (p.getZ() > l.fZmax)
        p.setZ(l.fZmax - tiny);
    }
  }

  // convert back the point to the world coordinate
  p = vol_uid->fTouchable.GetTopTransform().InverseTransformPoint(p);

  // store
  fOutputBlurAttribute->Fill3Value(p);
}

double GateDigitizerSpatialBlurringActor::ComputeTruncatedGaussianSigma(
    const G4double mu, const G4double sigma, const G4double lowLimit,
    const G4double highLimit) {
  const double lowLim_std = (lowLimit - mu) / sigma;
  const double hiLim_std = (highLimit - mu) / sigma;

  const double phi_lowLim = pdf(lowLim_std);
  const double phi_hiLim = pdf(hiLim_std);
  const double Fl = cdf(lowLim_std);
  const double Fh = cdf(hiLim_std);

  const double Z = Fh - Fl;
  const double mean_shift = (phi_lowLim - phi_hiLim) / Z;
  const double variance_correction =
      1 - (lowLim_std * phi_lowLim - hiLim_std * phi_hiLim) / Z -
      mean_shift * mean_shift;

  // Due to the double asymetrical truncation (both edges), an extra edge
  // correction is needed Through analytical tests an exponential correction was
  // found to fit the results within 5% error

  const double edgeCorrectedSigma = ComputeEdgeCorrectedSigma(
      mu, sigma * sqrt(variance_correction), lowLimit, highLimit);
  return edgeCorrectedSigma;
}

double GateDigitizerSpatialBlurringActor::ComputeEdgeCorrectedSigma(
    const double mu, const double sigma, const double lowLimit,
    const double highLimit) {
  constexpr double A = 3.61070188;
  constexpr double B = -0.86538264;

  // Distance to nearest edge
  double delta = std::min(mu - lowLimit, highLimit - mu);
  delta = std::max(0., delta); // Ensure it's not negative

  double delta_norm = delta / sigma;
  double correction = 1;

  // These cuts on delta_norm > 0.95 and delta_norm < 4 are needed to comply
  // with the safe limits of the fit.
  delta_norm = std::max(.95, delta_norm);
  if (delta_norm < 4)
    correction = A * std::exp(B * delta_norm);

  // Return corrected sigma
  return sigma * correction;
}

// Standard normal PDF
G4double GateDigitizerSpatialBlurringActor::pdf(G4double x) {
  return exp(-0.5 * x * x) / sqrt(2.0 * M_PI);
}

// Standard normal CDF using the error function
G4double GateDigitizerSpatialBlurringActor::cdf(G4double x) {
  return 0.5 * (1 + erf(x / sqrt(2.0)));
}
