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
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "GateVActor.h"

GateBioDoseActor::GateBioDoseActor(py::dict &user_info):
  GateVActor(user_info, false)
{
}

void GateBioDoseActor::InitializeUserInput(py::dict &user_info) {
  GateVActor::InitializeUserInput(user_info);

  fTranslation = DictGetG4ThreeVector(user_info, "translation");

  std::string const cellLine = DictGetStr(user_info, "cell_line");
  std::string const bioPhysicalModel = DictGetStr(user_info, "biophysical_model");
  std::string biophysicalModelPath = "data/" + cellLine + "_" + bioPhysicalModel + ".db";
  loadBiophysicalModel(biophysicalModelPath);
}

void GateBioDoseActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  fEdepImage = Image::New();
}

void GateBioDoseActor::BeginOfRunActionMasterThread(int run_id) {
  GateVActor::BeginOfRunActionMasterThread(run_id);

  fNbOfEvent = 0;

  AttachImageToVolume<Image>(fEdepImage, fPhysicalVolumeName, fTranslation);

  auto sp = fEdepImage->GetSpacing();
  // fVoxelVolume = sp[0] * sp[1] * sp[2];

  // compute volume of a dose voxel
  Image::RegionType region = fEdepImage->GetLargestPossibleRegion();
  // size_edep = region.GetSize();
}

int GateBioDoseActor::EndOfRunActionMasterThread(int run_id) {
  return GateVActor::EndOfRunActionMasterThread(run_id);
}

void GateBioDoseActor::BeginOfRunAction(const G4Run *) {
}

void GateBioDoseActor::BeginOfEventAction(const G4Event *event) {
  ++fNbOfEvent;
}

void GateBioDoseActor::EndOfEventAction(const G4Event *) {
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

  ImageAddValue<Image>(fEdepImage, index, energyDep);
}

void GateBioDoseActor::EndSimulationAction() {
}

void GateBioDoseActor::updateData() {
}

void GateBioDoseActor::loadBiophysicalModel(std::string const& filepath) {
  std::ifstream f(filepath);
    if(!f) {
    // GateError("BioDoseActor " << GetName() << ": unable to open file '" << filepath << "'");
    return; // TODO
  }

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
