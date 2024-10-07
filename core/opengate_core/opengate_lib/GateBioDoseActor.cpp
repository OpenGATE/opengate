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

  std::string const cellLine = DictGetStr(user_info, "cell_line");
  std::string const bioPhysicalModel = DictGetStr(user_info, "biophysical_model");
  std::string biophysicalModelPath = "data/" + cellLine + "_" + bioPhysicalModel + ".db";
  loadBiophysicalModel(biophysicalModelPath);
}

void GateBioDoseActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  fEdepImage = Image::New();
  fDoseImage = Image::New();
  fAlphaMixImage = Image::New();
  fSqrtBetaMixImage = Image::New();

  // C++-side images
  fEventEdepImage = Image::New();
  fEventDoseImage = Image::New();
  fEventAlphaImage = Image::New();
  fEventSqrtBetaImage = Image::New();
}

void GateBioDoseActor::BeginOfRunActionMasterThread(int run_id) {
  GateVActor::BeginOfRunActionMasterThread(run_id);

  fNbOfEvent = 0;

  AttachImageToVolume<Image>(fEdepImage, fPhysicalVolumeName, fTranslation);
  AttachImageToVolume<Image>(fDoseImage, fPhysicalVolumeName, fTranslation);

  // C++-side images
  fEventEdepImage->SetRegions(fEdepImage->GetLargestPossibleRegion());
  fEventEdepImage->Allocate();
  fEventDoseImage->SetRegions(fEdepImage->GetLargestPossibleRegion());
  fEventDoseImage->Allocate();
  fEventAlphaImage->SetRegions(fEdepImage->GetLargestPossibleRegion());
  fEventAlphaImage->Allocate();
  fEventSqrtBetaImage->SetRegions(fEdepImage->GetLargestPossibleRegion());
  fEventSqrtBetaImage->Allocate();

  auto const& sp = fEdepImage->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
}

int GateBioDoseActor::EndOfRunActionMasterThread(int run_id) {
  return GateVActor::EndOfRunActionMasterThread(run_id);
}

void GateBioDoseActor::BeginOfRunAction(const G4Run *) {
}

void GateBioDoseActor::BeginOfEventAction(const G4Event *event) {
  ++fNbOfEvent;

  fEventVoxelIndices.clear();

  fEventEdepImage->FillBuffer(0);
  fEventDoseImage->FillBuffer(0);
  fEventAlphaImage->FillBuffer(0);
  fEventSqrtBetaImage->FillBuffer(0);
}

void GateBioDoseActor::EndOfEventAction(const G4Event *) {
  for(auto const& index: fEventVoxelIndices) {
    auto const eventEdep = fEventEdepImage->GetPixel(index);
    auto const eventDose = fEventDoseImage->GetPixel(index);
    auto const eventAlphaMix = fEventAlphaImage->GetPixel(index) / eventEdep;
    auto const eventSqrtBetaMix = fEventSqrtBetaImage->GetPixel(index) / eventEdep;

    fVoxelIndices.insert(index);

    ImageAddValue<Image>(fEdepImage, index, eventEdep);
    ImageAddValue<Image>(fDoseImage, index, eventDose);
    ImageAddValue<Image>(fAlphaMixImage, index, eventAlphaMix);
    ImageAddValue<Image>(fSqrtBetaMixImage, index, eventSqrtBetaMix);
  }
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
  double const energyDep  = step->GetTotalEnergyDeposit() / CLHEP::MeV * weight;

  if (energyDep <= 0) return;

  // compute event values
  auto const* currentMaterial = step->GetPreStepPoint()->GetMaterial();
  double const density = currentMaterial->GetDensity();
  double const mass = fVoxelVolume * density;
  double const dose = energyDep / mass / CLHEP::gray;

  ImageAddValue<Image>(fEventEdepImage, index, energyDep);
  ImageAddValue<Image>(fEventDoseImage, index, dose);

  // Get information from step
  // Particle
  G4int nZ = step->GetTrack()->GetDefinition()->GetAtomicNumber();
  double kineticEnergyPerNucleon = (step->GetPreStepPoint()->GetKineticEnergy()) / (step->GetTrack()->GetDefinition()->GetAtomicMass());

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

    double alpha = (interpol.alpha.a * kineticEnergyPerNucleon + interpol.alpha.b) * energyDep;
    double sqrtBeta = (interpol.sqrtBeta.a * kineticEnergyPerNucleon + interpol.sqrtBeta.b) * energyDep;

    if(alpha < 0) alpha = 0;
    if(sqrtBeta < 0) sqrtBeta = 0;

    // Accumulate alpha/beta
    ImageAddValue<Image>(fEventAlphaImage, index, alpha);
    ImageAddValue<Image>(fEventSqrtBetaImage, index, sqrtBeta);

    fEventVoxelIndices.insert(index);
  }
}

void GateBioDoseActor::EndSimulationAction() {
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
