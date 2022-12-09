/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerBlurringActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <Randomize.hh>
#include <iostream>

GateDigitizerBlurringActor::GateDigitizerBlurringActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {

  // actions
  fActions.insert("EndOfEventAction");

  // blurring method
  fBlurAttributeName = DictGetStr(user_info, "blur_attribute");
  fBlurMethod = DictGetStr(user_info, "blur_method");
  fBlurSigma = DictGetDouble(user_info, "blur_sigma");
  fBlurReferenceValue = DictGetDouble(user_info, "blur_reference_value");
  fBlurResolution = DictGetDouble(user_info, "blur_resolution");
  fBlurSlope = DictGetDouble(user_info, "blur_slope");
  if (fBlurMethod == "Gaussian")
    fBlurValue = [&](double v) { return this->GaussianBlur(v); };
  if (fBlurMethod == "InverseSquare")
    fBlurValue = [&](double v) { return this->InverseSquare(v); };
  if (fBlurMethod == "Linear")
    fBlurValue = [&](double v) { return this->Linear(v); };

  DDD(fBlurSigma);
}

GateDigitizerBlurringActor::~GateDigitizerBlurringActor() = default;

void GateDigitizerBlurringActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  DDD("StartSimulation");
  auto a = attributes_not_in_filler;
  a.push_back(fBlurAttributeName);
  GateVDigitizerWithOutputActor::DigitInitialize(a);
  DDDV(a);

  // set output pointers to the attributes needed for computation
  fOutputBlurAttribute =
      fOutputDigiCollection->GetDigiAttribute(fBlurAttributeName);
  DDD(fBlurAttributeName);

  // set input pointers to the attributes needed for computation
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  lr.fInputIter.TrackAttribute(fBlurAttributeName, &l.fAttDValue);
  DDD("ici");
}

void GateDigitizerBlurringActor::EndOfEventAction(const G4Event * /*unused*/) {
  // loop on all digi of this events
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &iter = lr.fInputIter;
  iter.GoToBegin();
  DDD(fInputDigiCollection->GetSize());
  while (!iter.IsAtEnd()) {
    // blur the current value
    auto v = fBlurValue(*l.fAttDValue);
    fOutputBlurAttribute->FillDValue(v);
    // copy the other attributes
    auto &i = lr.fInputIter.fIndex;
    DDD(i);
    lr.fDigiAttributeFiller->Fill(i);
    iter++;
  }
  DDD(fOutputDigiCollection->GetSize());
}

double GateDigitizerBlurringActor::GaussianBlur(double value, double sigma) {
  // https://github.com/OpenGATE/Gate/blob/develop/source/digits_hits/src/GateLocalTimeResolution.cc
  return G4RandGauss::shoot(value, sigma);
}

double GateDigitizerBlurringActor::GaussianBlur(double value) {
  return GaussianBlur(value, fBlurSigma);
}

double GateDigitizerBlurringActor::InverseSquare(double value) {
  // https://github.com/OpenGATE/Gate/blob/develop/source/digits_hits/src/GateBlurring.cc
  // https://github.com/OpenGATE/Gate/blob/develop/source/digits_hits/src/GateInverseSquareBlurringLaw.cc
  auto v = fBlurResolution * (sqrt(fBlurReferenceValue) / sqrt(value));
  auto x = G4RandGauss::shoot(value, (v * value) * fwhm_to_sigma);
  return x;
}

double GateDigitizerBlurringActor::Linear(double value) {
  // https://github.com/OpenGATE/Gate/blob/develop/source/digits_hits/src/GateBlurring.cc
  // https://github.com/OpenGATE/Gate/blob/develop/source/digits_hits/src/GateLinearBlurringLaw.cc
  auto v = fBlurSlope * (value - fBlurReferenceValue) + fBlurResolution;
  auto x = G4RandGauss::shoot(value, (v * value) * fwhm_to_sigma);
  return x;
}
