/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerGaussianBlurringActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <Randomize.hh>
#include <iostream>

GateDigitizerGaussianBlurringActor::GateDigitizerGaussianBlurringActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {

  // actions
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");

  // options
  fOutputFilename = DictGetStr(user_info, "output");
  fOutputDigiCollectionName = DictGetStr(user_info, "_name");
  fInputDigiCollectionName = DictGetStr(user_info, "input_digi_collection");
  fUserSkipDigiAttributeNames = DictGetVecStr(user_info, "skip_attributes");
  fClearEveryNEvents = DictGetInt(user_info, "clear_every");

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

  // init
  fOutputDigiCollection = nullptr;
  fInputDigiCollection = nullptr;
}

GateDigitizerGaussianBlurringActor::~GateDigitizerGaussianBlurringActor() =
    default;

void GateDigitizerGaussianBlurringActor::StartSimulationAction() {
  // Get the input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  fInputDigiCollection = hcm->GetDigiCollection(fInputDigiCollectionName);
  CheckRequiredAttribute(fInputDigiCollection, fBlurAttributeName);

  // Create the list of output attributes
  auto names = fInputDigiCollection->GetDigiAttributeNames();
  for (const auto &n : fUserSkipDigiAttributeNames) {
    if (names.count(n) > 0)
      names.erase(n);
  }

  // Create the output hits collection with the same list of attributes
  fOutputDigiCollection = hcm->NewDigiCollection(fOutputDigiCollectionName);
  fOutputDigiCollection->SetFilename(fOutputFilename);
  fOutputDigiCollection->InitializeDigiAttributes(names);
  fOutputDigiCollection->InitializeRootTupleForMaster();
}

void GateDigitizerGaussianBlurringActor::BeginOfRunAction(const G4Run *run) {
  if (run->GetRunID() == 0)
    InitializeComputation();
}

void GateDigitizerGaussianBlurringActor::InitializeComputation() {
  fOutputDigiCollection->InitializeRootTupleForWorker();

  // Create Filler of all remaining attributes (except the required ones)
  auto &l = fThreadLocalData.Get();
  auto names = fOutputDigiCollection->GetDigiAttributeNames();
  names.erase(fBlurAttributeName);
  l.fDigiAttributeFiller = new GateDigiAttributesFiller(
      fInputDigiCollection, fOutputDigiCollection, names);

  // set output pointers to the attributes needed for computation
  fOutputBlurAttribute =
      fOutputDigiCollection->GetDigiAttribute(fBlurAttributeName);

  // set input pointers to the attributes needed for computation
  l.fInputIter = fInputDigiCollection->NewIterator();
  l.fInputIter.TrackAttribute(fBlurAttributeName, &l.fAttValue);
}

void GateDigitizerGaussianBlurringActor::BeginOfEventAction(
    const G4Event *event) {
  bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  fOutputDigiCollection->FillToRootIfNeeded(must_clear);
}

void GateDigitizerGaussianBlurringActor::EndOfEventAction(
    const G4Event * /*unused*/) {
  // loop on all hits to group per volume ID
  auto &l = fThreadLocalData.Get();
  auto &iter = l.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    auto &i = l.fInputIter.fIndex;
    auto v = fBlurValue(*l.fAttValue);
    fOutputBlurAttribute->FillDValue(v);
    l.fDigiAttributeFiller->Fill(i);
    iter++;
  }
}

double GateDigitizerGaussianBlurringActor::GaussianBlur(double value) {
  return G4RandGauss::shoot(value, fBlurSigma);
}

double GateDigitizerGaussianBlurringActor::InverseSquare(double value) {
  auto v = fBlurResolution * (sqrt(fBlurReferenceValue) / sqrt(value));
  auto x = G4RandGauss::shoot(value, (v * value) * fwhm_to_sigma);
  return x;
}

double GateDigitizerGaussianBlurringActor::Linear(double value) {
  auto v = fBlurSlope * (value - fBlurReferenceValue) + fBlurResolution;
  auto x = G4RandGauss::shoot(value, (v * value) * fwhm_to_sigma);
  return x;
}

// Called every time a Run ends
void GateDigitizerGaussianBlurringActor::EndOfRunAction(
    const G4Run * /*unused*/) {
  fOutputDigiCollection->FillToRootIfNeeded(true);
  auto &iter = fThreadLocalData.Get().fInputIter;
  iter.Reset();
}

// Called every time a Run ends
void GateDigitizerGaussianBlurringActor::EndOfSimulationWorkerAction(
    const G4Run * /*unused*/) {
  fOutputDigiCollection->Write();
}

// Called when the simulation end
void GateDigitizerGaussianBlurringActor::EndSimulationAction() {
  fOutputDigiCollection->Write();
  fOutputDigiCollection->Close();
}
