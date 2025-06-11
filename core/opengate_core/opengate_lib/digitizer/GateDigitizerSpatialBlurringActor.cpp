/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerSpatialBlurringActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersGeometry.h"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <G4Navigator.hh>
#include <G4VoxelLimits.hh>
#include <Randomize.hh>
#include <iostream>
#define _USE_MATH_DEFINES
#include <cmath>

GateDigitizerSpatialBlurringActor::GateDigitizerSpatialBlurringActor(
    py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {

  // actions
  fActions.insert("EndOfEventAction");
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

  CheckRequiredAttribute(fInputDigiCollection, "PostStepUniqueVolumeID");

  // set output pointers to the attributes needed for computation
  fOutputBlurAttribute =
      fOutputDigiCollection->GetDigiAttribute(fBlurAttributeName);

  // set input pointers to the attributes needed for computation
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  lr.fInputIter.TrackAttribute(fBlurAttributeName, &l.fAtt3Value);
  lr.fInputIter.TrackAttribute("PostStepUniqueVolumeID", &l.fVolumeId);
}

void GateDigitizerSpatialBlurringActor::BeginOfRunAction(const G4Run *run) {
  GateVDigitizerWithOutputActor::BeginOfRunAction(run);
  G4ThreeVector translation;
  G4RotationMatrix rotation;
  ComputeTransformationFromWorldToVolume(fAttachedToVolumeName, translation,
                                         rotation);
  fWorldToVolume = G4AffineTransform(rotation.inverse(), translation);

  ComputeTransformationFromVolumeToWorld(fAttachedToVolumeName, translation,
                                         rotation, true);
  fVolumeToWorld = G4AffineTransform(rotation.inverse(), translation);

  if (run->GetRunID() == 0) {
    // Init a navigator that will be used to find the transform
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto world = pvs->GetVolume("world");
    auto &l = fThreadLocalData.Get();
    l.fNavigator = new G4Navigator();
    l.fNavigator->SetWorldVolume(world);
  } else {
    auto &l = fThreadLocalData.Get();
    l.fNavigator->ResetStackAndState();
  }
}

void GateDigitizerSpatialBlurringActor::EndOfEventAction(
    const G4Event * /*unused*/) {
  // loop on all digi of this events
  // auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &iter = lr.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    // blur the current value
    BlurCurrentThreeVectorValue();
    // copy the other attributes
    auto &i = lr.fInputIter.fIndex;
    lr.fDigiAttributeFiller->Fill(i);
    iter++;
  }
}

void GateDigitizerSpatialBlurringActor::BlurCurrentThreeVectorValue() {
  // Get the current position
  auto &l = fThreadLocalData.Get();
  auto &vec = *l.fAtt3Value;

  // locate to find the volume that contains the point
  G4VPhysicalVolume *phys_vol;
  if (fKeepInSolidLimits) {
    G4TouchableHistory fTouchableHistory;
    l.fNavigator->LocateGlobalPointAndUpdateTouchable(vec, &fTouchableHistory);
    auto vid = GateUniqueVolumeID::New(&fTouchableHistory);
    phys_vol = vid->GetVolumeDepthID().back().fVolume;
    // If the volume is parameterised, we consider the parent volume to compute
    // the extent (otherwise the keep in solid will consider one single instance
    // of the repeated solid, instead of the whole parameterised volume).
    if (phys_vol->IsParameterised()) {
      auto n = vid->GetVolumeDepthID().size();
      phys_vol = vid->GetVolumeDepthID()[n - 2].fVolume;
    }
  }

  // consider local position
  auto v = fWorldToVolume.TransformPoint(vec);
  G4ThreeVector p(G4RandGauss::shoot(v.getX(), fBlurSigma3.getX()),
                  G4RandGauss::shoot(v.getY(), fBlurSigma3.getY()),
                  G4RandGauss::shoot(v.getZ(), fBlurSigma3.getZ()));

  if (fKeepInSolidLimits) {
    // check limits according to the volume
    G4VoxelLimits limits;
    G4double Xmin, Xmax, Ymin, Ymax, Zmin, Zmax;
    G4AffineTransform at;

    auto solid = phys_vol->GetLogicalVolume()->GetSolid();
    solid->CalculateExtent(kXAxis, limits, at, Xmin, Xmax);
    solid->CalculateExtent(kYAxis, limits, at, Ymin, Ymax);
    solid->CalculateExtent(kZAxis, limits, at, Zmin, Zmax);

    static const double tiny = 1 * CLHEP::nm;

    if (fUseTruncatedGaussian) {
      G4double newX(p.getX()), newY(p.getY()), newZ(p.getZ()), newSigmaX,
          newSigmaY, newSigmaZ;

      newSigmaX = (ComputeTruncatedGaussianSigma(v.getX(), fBlurSigma3.getX(),
                                                 Xmin, Xmax));
      newSigmaY = (ComputeTruncatedGaussianSigma(v.getY(), fBlurSigma3.getY(),
                                                 Ymin, Ymax));
      newSigmaZ = (ComputeTruncatedGaussianSigma(v.getZ(), fBlurSigma3.getZ(),
                                                 Zmin, Zmax));

      // std::cout<<<newSigmaX<<","<<std::endl;

      while ((newX > Xmax) || (newX < Xmin))
        newX = G4RandGauss::shoot(v.getX(), newSigmaX);
      while ((newY > Ymax) || (newY < Ymin))
        newY = G4RandGauss::shoot(v.getY(), newSigmaY);
      while ((newZ > Zmax) || (newZ < Zmin))
        newZ = G4RandGauss::shoot(v.getZ(), newSigmaZ);

      p.setX(newX);
      p.setY(newY);
      p.setZ(newZ);
    }

    else {
      if (p.getX() < Xmin)
        p.setX(Xmin + tiny);
      if (p.getY() < Ymin)
        p.setY(Ymin + tiny);
      if (p.getZ() < Zmin)
        p.setZ(Zmin + tiny);

      if (p.getX() > Xmax)
        p.setX(Xmax - tiny);
      if (p.getY() > Ymax)
        p.setY(Ymax - tiny);
      if (p.getZ() > Zmax)
        p.setZ(Zmax - tiny);
    }
  }

  // convert back to global position
  p = fVolumeToWorld.TransformPoint(p);

  // store
  fOutputBlurAttribute->Fill3Value(p);
}

double GateDigitizerSpatialBlurringActor::ComputeTruncatedGaussianSigma(
    G4double mu, G4double sigma, G4double lowLimit, G4double highLimit) {

  double lowLim_std = (lowLimit - mu) / sigma;
  double hiLim_std = (highLimit - mu) / sigma;

  double phi_lowLim = pdf(lowLim_std);
  double phi_hiLim = pdf(hiLim_std);
  double Fl = cdf(lowLim_std);
  double Fh = cdf(hiLim_std);

  double Z = Fh - Fl;
  double mean_shift = (phi_lowLim - phi_hiLim) / Z;
  double variance_correction =
      1 - (lowLim_std * phi_lowLim - hiLim_std * phi_hiLim) / Z -
      mean_shift * mean_shift;

  // Due to the double asymetrical truncation (both edges), an extra edge
  // correction is needed Through analytical tests an exponential correction was
  // found to fit the results within 5% error

  double edgeCorrectedSigma = ComputeEdgeCorrectedSigma(
      mu, sigma * sqrt(variance_correction), lowLimit, highLimit);
  return edgeCorrectedSigma;
}

double GateDigitizerSpatialBlurringActor::ComputeEdgeCorrectedSigma(
    double mu, double sigma, double lowLimit, double highLimit) {

  const double A = 3.61070188;
  const double B = -0.86538264;

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
//___________________________________________________________________
// Standard normal CDF using the error function
G4double GateDigitizerSpatialBlurringActor::cdf(G4double x) {
  return 0.5 * (1 + erf(x / sqrt(2.0)));
}
