/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include <fstream>
#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>

#include "G4RunManager.hh"

#include "GateBioDoseActor.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "GateVActor.h"

GateBioDoseActor::GateBioDoseActor(py::dict &user_info):
  GateVActor(user_info, false)
{
}

void GateBioDoseActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);

  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fAlphaRef = DictGetDouble(user_info, "alpha_ref");
  fBetaRef = DictGetDouble(user_info, "beta_ref");

  std::string const cellLine = DictGetStr(user_info, "cell_line");
  std::string const bioPhysicalModel = DictGetStr(user_info, "biophysical_model");
  std::string const biophysicalModelPath = "data/" + cellLine + "_" + bioPhysicalModel + ".db";
  loadBiophysicalModel(biophysicalModelPath);
}

void GateBioDoseActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  fHitEventCountImage = Image::New();
  fEdepImage = Image::New();
  fDoseImage = Image::New();
  fAlphaMixImage = Image::New();
  fSqrtBetaMixImage = Image::New();
  fAlphaMixDoseImage = Image::New();
  fSqrtBetaMixDoseImage = Image::New();

  fSumAlphaMixImage = Image::New();
  fSumSqrtBetaMixImage = Image::New();
  fSumAlphaMixDoseImage = Image::New();
  fSumSqrtBetaMixDoseImage = Image::New();

  // C++-side images
  fEventEdepImage = Image::New();
  fEventDoseImage = Image::New();
  fEventSumAlphaMixDoseImage = Image::New();
  fEventSumSqrtBetaMixDoseImage = Image::New();
}

void GateBioDoseActor::BeginOfRunActionMasterThread(int run_id) {
  GateVActor::BeginOfRunActionMasterThread(run_id);

  fNbOfEvent = 0;

  AttachImageToVolume<Image>(fHitEventCountImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fEdepImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fDoseImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fAlphaMixImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fSqrtBetaMixImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fAlphaMixDoseImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fSqrtBetaMixDoseImage, fPhysicalVolumeName, fTranslation);

  AttachImageToVolume<Image>(fSumAlphaMixImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fSumSqrtBetaMixImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fSumAlphaMixDoseImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fSumSqrtBetaMixDoseImage, fPhysicalVolumeName, fTranslation);

  // C++-side images
  auto initCppImage = [this](Image::Pointer image) {
    image->SetRegions(fEdepImage->GetLargestPossibleRegion());
    image->Allocate();
  };

  initCppImage(fEventEdepImage);
  initCppImage(fEventDoseImage);
  initCppImage(fEventSumAlphaMixDoseImage);
  initCppImage(fEventSumSqrtBetaMixDoseImage);

  auto const& sp = fEdepImage->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
}

int GateBioDoseActor::EndOfRunActionMasterThread(int run_id) {
  return GateVActor::EndOfRunActionMasterThread(run_id);
}

void GateBioDoseActor::BeginOfRunAction(const G4Run *run) {
  GateVActor::BeginOfRunAction(run);
}

void GateBioDoseActor::BeginOfEventAction(const G4Event *event) {
  GateVActor::BeginOfEventAction(event);

  ++fNbOfEvent;

  fEventVoxelIndices.clear();

  fEventEdepImage->FillBuffer(0);
  fEventDoseImage->FillBuffer(0);
  fEventSumAlphaMixDoseImage->FillBuffer(0);
  fEventSumSqrtBetaMixDoseImage->FillBuffer(0);
}

void GateBioDoseActor::EndOfEventAction(const G4Event *event) {
  GateVActor::EndOfEventAction(event);

  double totalEventEdep = 0;
  double totalEventDose = 0;
  for(auto const& index: fEventVoxelIndices) {
    auto const eventEdep = fEventEdepImage->GetPixel(index);
    auto const eventDose = fEventDoseImage->GetPixel(index);
    auto const eventSumAlphaMixDose = fEventSumAlphaMixDoseImage->GetPixel(index);
    auto const eventSumSqrtBetaMixDose = fEventSumSqrtBetaMixDoseImage->GetPixel(index);

    totalEventEdep += eventEdep;
    totalEventDose += eventDose;

    fVoxelIndices.insert(arrayFromItkIndex(index));
    ImageAddValue<Image>(fHitEventCountImage, index, 1);

    ImageAddValue<Image>(fEdepImage, index, eventEdep);
    ImageAddValue<Image>(fDoseImage, index, eventDose);
    ImageAddValue<Image>(fSumAlphaMixDoseImage, index, eventSumAlphaMixDose);
    ImageAddValue<Image>(fSumSqrtBetaMixDoseImage, index, eventSumSqrtBetaMixDose);
  }

  fmt::print("total event edep: {}\n", totalEventEdep);
  fmt::print("total event dose: {}\n", totalEventDose);
}

void GateBioDoseActor::SteppingAction(G4Step *step) {
  auto const& preGlobal = step->GetPreStepPoint()->GetPosition();
  auto const& postGlobal = step->GetPostStepPoint()->GetPosition();
  auto const& touchable = step->GetPreStepPoint()->GetTouchable();

  // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?
  // consider random position between pre and post
  auto position = postGlobal;
  if (fHitType == "pre") {
    position = preGlobal;
  } else if (fHitType == "random") {
    auto x = G4UniformRand();
    auto direction = postGlobal - preGlobal;
    position = preGlobal + x * direction;
  } else if (fHitType == "middle") {
    auto direction = postGlobal - preGlobal;
    position = preGlobal + 0.5 * direction;
  }

  auto localPosition =
    touchable->GetHistory()->GetTransform(0).TransformPoint(position);

  // convert G4ThreeVector to itk PointType
  Image::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  Image::IndexType index;
  bool isInside = fEdepImage->TransformPhysicalPointToIndex(point, index);

  if (!isInside) return;

  double const weight     = step->GetTrack()->GetWeight();
  double const energyDep  = step->GetTotalEnergyDeposit() * weight;

  if (energyDep <= 0) return;

  ImageAddValue<Image>(fEventEdepImage, index, energyDep);

  // compute event values
  auto const* currentMaterial = step->GetPreStepPoint()->GetMaterial();
  double const density = currentMaterial->GetDensity();
  double const mass = fVoxelVolume * density;
  double const dose = energyDep / mass / CLHEP::gray;

  ImageAddValue<Image>(fEventDoseImage, index, dose);

  // Get information from step
  // Particle
  G4int nZ = step->GetTrack()->GetDefinition()->GetAtomicNumber();
  double kineticEnergyPerNucleon = (step->GetPreStepPoint()->GetKineticEnergy()) / (step->GetTrack()->GetDefinition()->GetAtomicMass());

  // TODO check performances effect of duplicating this
  // to handle specifically known ions cases
  ++fStepCount;

  // Accumulation of alpha/beta if ion type if known
  // -> check if the ion type is known
  if(fEnergyMaxForZ.count(nZ) != 0) {
    ++fStepWithKnownIonCount;

    double energyMax = fEnergyMaxForZ.at(nZ);

    AlphaBetaInterpolTable::const_iterator itInterpol;
    if(kineticEnergyPerNucleon >= energyMax) {
    	Fragment fragmentKineticEnergyMax{nZ, energyMax};
    	itInterpol = fAlphaBetaInterpolTable.find(fragmentKineticEnergyMax);
    } else {
    	Fragment fragmentKineticEnergy{nZ, kineticEnergyPerNucleon};
    	itInterpol = fAlphaBetaInterpolTable.upper_bound(fragmentKineticEnergy);
    }

    // Calculation of alphaDep and betaDep (K = (a*Z+b)*E)
    auto const& interpol = (*itInterpol).second;

    double alpha = interpol.alpha.a * kineticEnergyPerNucleon + interpol.alpha.b;
    double sqrtBeta = interpol.sqrtBeta.a * kineticEnergyPerNucleon + interpol.sqrtBeta.b;

    if(alpha < 0) alpha = 0;
    if(sqrtBeta < 0) sqrtBeta = 0;

		ImageAddValue<Image>(fSumAlphaMixImage, index, alpha * energyDep);
		ImageAddValue<Image>(fSumSqrtBetaMixImage, index, sqrtBeta * energyDep);

		// Accumulate weighted alpha/sqrt(beta)
		ImageAddValue<Image>(fEventSumAlphaMixDoseImage, index, alpha * dose);
		ImageAddValue<Image>(fEventSumSqrtBetaMixDoseImage, index, sqrtBeta * dose);

		fEventVoxelIndices.insert(index);
  }
}

void GateBioDoseActor::EndSimulationAction() {
  fmt::print("{} / {} = {}%\n", fStepWithKnownIonCount, fStepCount, 100. * fStepWithKnownIonCount / fStepCount);
}

void GateBioDoseActor::updateData() {
}

void GateBioDoseActor::loadBiophysicalModel(std::string const& filepath) {
  std::ifstream f(filepath);
  if(!f) Fatal("[BioDoseActor] unable to open file '" + filepath + "'");

  int nZ = 0;
  double prevKineticEnergy = 1;
  double prevAlpha = 1;
  double prevBeta =1;

  auto interpolCoefficientsFor = [](double x1, double x2, double y1, double y2) {
    double a = (y2 - y1) / (x2 - x1);
    double b = y1 - x1 * a;
    return Coefficients{a, b};
  };

  for(std::string line; std::getline(f, line); ) {
    std::istringstream iss(line);
    std::string firstCol;

    iss >> firstCol;

    if(firstCol == "Fragment") {
      if(nZ != 0) // prevKineticEnergy is the maximum kinetic energy for current nZ
        fEnergyMaxForZ[nZ] = prevKineticEnergy;

      iss >> nZ;
      prevKineticEnergy = 1;
      prevAlpha = 1;
      prevBeta = 1;
    } else if(nZ != 0) {
      double kineticEnergy = 0;
      double alpha = 0;
      double beta = 0;
      std::istringstream{firstCol} >> kineticEnergy;
      iss >> alpha;
      iss >> beta;

      auto alphaCoeff = interpolCoefficientsFor(prevKineticEnergy, kineticEnergy, prevAlpha, alpha);
      auto sqrtBetaCoeff = interpolCoefficientsFor(prevKineticEnergy, kineticEnergy, std::sqrt(prevBeta), std::sqrt(beta));

      // Saving the in the input databse
      Fragment fragment{nZ, kineticEnergy};
      fAlphaBetaInterpolTable[fragment] = {alphaCoeff, sqrtBetaCoeff};

      prevKineticEnergy = kineticEnergy;
      prevAlpha = alpha;
      prevBeta = beta;
    } else {
      // GateError("BioDoseActor " << GetName() << ": bad database format in '" << filepath << "'");
      return; // TODO
    }
  }

  if(nZ != 0) // last line read; prevKineticEnergy is the maximum kinetic energy for current nZ
    fEnergyMaxForZ[nZ] = prevKineticEnergy;
}
