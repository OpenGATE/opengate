/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>

#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateBioDoseActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

GateBioDoseActor::GateBioDoseActor(py::dict &user_info):
  GateVActor(user_info, true),
  fInitialTranslation(DictGetG4ThreeVector(user_info, "translation")),
  fHitType(DictGetStr(user_info, "hit_type")),
  fBioDoseImage(Image::New()),
  fEdepFlag(DictGetBool(user_info, "edep")),
  fDoseFlag(DictGetBool(user_info, "dose")),
  fAlphaMixFlag(DictGetBool(user_info, "alphamix")),
  fSqrtBetaMixFlag(DictGetBool(user_info, "sqrtbetamix")),
  fRBEFlag(DictGetBool(user_info, "rbe")),
  fUncertaintyFlag(DictGetBool(user_info, "uncertainty"))
{
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndSimulationAction");

  std::string const cellLine = DictGetStr(user_info, "cell_line");
  std::string const bioPhysicalModel = DictGetStr(user_info, "biophysical_model");
  std::string biophysicalModelPath = "data/" + cellLine + "_" + bioPhysicalModel + ".db";
  loadBiophysicalModel(biophysicalModelPath);
}

void GateBioDoseActor::ActorInitialize() {
  if(fEdepFlag)         fEdepImage = Image::New();
  if(fDoseFlag)         fDoseImage = Image::New();
  if(fAlphaMixFlag)     fAlphaMixImage = Image::New();
  if(fSqrtBetaMixFlag)  fSqrtBetaMixImage = Image::New();
  if(fRBEFlag)          fRBEImage = Image::New();
  if(fUncertaintyFlag) {
    fBioDoseUncertaintyImage = Image::New();
    fEventEdepImage = Image::New();
    fEventDoseImage = Image::New();
    fSquaredDoseImage = Image::New();
    fEventAlphaImage = Image::New();
    fSquaredAlphaMixImage = Image::New();
    fEventSqrtBetaImage = Image::New();
    fSquaredSqrtBetaMixImage = Image::New();
    fAlphaMixSqrtBetaMixImage = Image::New();
    fAlphaMixDoseImage = Image::New();
    fSqrtBetaMixDoseImage = Image::New();
  }
}

void GateBioDoseActor::BeginOfRunAction(const G4Run *) {
  Image::RegionType region = fBioDoseImage->GetLargestPossibleRegion();
  auto regionSize = region.GetSize();
  if(fUncertaintyFlag) {
    auto images = {
      fBioDoseUncertaintyImage, fEventEdepImage, fEventDoseImage, fSquaredDoseImage,
      fEventAlphaImage, fSquaredAlphaMixImage, fEventSqrtBetaImage, fSquaredSqrtBetaMixImage,
      fAlphaMixSqrtBetaMixImage, fAlphaMixDoseImage, fSqrtBetaMixDoseImage
    };
    for(auto& image: images) {
      image->SetRegions(regionSize);
      image->Allocate();
    }
  }
  // Important ! The volume may have moved, so we re-attach each run
  // AttachImageToVolume<Image>(cpp_edep_image, fPhysicalVolumeName, fInitialTranslation);
  // // compute volume of a dose voxel
  // auto sp = cpp_edep_image->GetSpacing();
  // fVoxelVolume = sp[0] * sp[1] * sp[2];
}

void GateBioDoseActor::BeginOfEventAction(const G4Event *event) {
  {
    G4AutoLock lock(&fNbOfEventMutex);
    ++fNbOfEvent;
  }

  {
    G4AutoLock lock(&fEventVoxelIndicesMutex);
    fEventVoxelIndices.clear();
  }

  {
    G4AutoLock lock(&fUncertaintyImagesMutex);
    fEventEdepImage->Initialize();
    fEventDoseImage->Initialize();
    fEventAlphaImage->Initialize();
    fEventSqrtBetaImage->Initialize();
  }
}

void GateBioDoseActor::EndOfEventAction(const G4Event *) {
  // TODO MT?
  for(auto const& index: fEventVoxelIndices) {
		auto const eventEdep = fEventEdepImage->GetPixel(index);
		auto const eventDose = fEventDoseImage->GetPixel(index);
		auto const eventAlphaMix = fEventAlphaImage->GetPixel(index) / eventEdep;
		auto const eventSqrtBetaMix = fEventSqrtBetaImage->GetPixel(index) / eventEdep;

		ImageAddValue<Image>(fSquaredDoseImage, index, eventDose * eventDose);
		ImageAddValue<Image>(fSquaredAlphaMixImage, index, eventAlphaMix * eventAlphaMix);
		ImageAddValue<Image>(fSquaredSqrtBetaMixImage, index, eventSqrtBetaMix * eventSqrtBetaMix);

		ImageAddValue<Image>(fAlphaMixSqrtBetaMixImage, index, eventAlphaMix * eventSqrtBetaMix);
		ImageAddValue<Image>(fAlphaMixDoseImage, index, eventAlphaMix * eventDose);
		ImageAddValue<Image>(fSqrtBetaMixDoseImage, index, eventSqrtBetaMix * eventDose);
  }
}

void GateBioDoseActor::SteppingAction(G4Step *step) {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto const* touchable = step->GetPreStepPoint()->GetTouchable();
  // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?

  auto position = postGlobal;
  if(fHitType == "pre") {
    position = preGlobal;
  } else if(fHitType == "random") {
    auto x = G4UniformRand();
    auto direction = postGlobal - preGlobal;
    position = preGlobal + x * direction;
  } else if(fHitType == "middle") {
    auto direction = postGlobal - preGlobal;
    position = preGlobal + 0.5 * direction;
  }
  auto localPosition = touchable->GetHistory()->GetTransform(0).TransformPoint(position);

  // convert G4ThreeVector to itk PointType
  Image::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  // get edep in MeV (take weight into account)
  auto w = step->GetTrack()->GetWeight();
  auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;

  // get pixel index
  Image::IndexType index;
  bool isInside = fBioDoseImage->TransformPhysicalPointToIndex(point, index);

  if(not isInside) return;

  double const weight     = step->GetTrack()->GetWeight();
  double const energyDep  = step->GetTotalEnergyDeposit() * weight;

  if(energyDep == 0)  return;

  decltype(fDepositedMap.begin()) it;
  {
    G4AutoLock lock(&fDepositedMutex);

    it = fDepositedMap.find(index);
    if(it == std::end(fDepositedMap)) {
      fDepositedMap[index] = {0, 0, 0, 0};
      it = fDepositedMap.find(index);
    }
  }

  auto& deposited = (*it).second;

  // Accumulate energy inconditionnaly
  {
    G4AutoLock lock(&fDepositedMutex);
    deposited.energy += energyDep;
  }

  auto* currentMaterial = step->GetPreStepPoint()->GetMaterial();
  double density = currentMaterial->GetDensity();
  auto sp = fBioDoseImage->GetSpacing(); // TODO move to run only once
  auto voxelVolume = sp[0] * sp[1] * sp[2];
  double mass = voxelVolume * density;
  double dose = energyDep / mass / CLHEP::gray;

  {
    G4AutoLock lock(&fDepositedMutex);
    deposited.dose += dose;
  }

  if(fUncertaintyFlag) {
    G4AutoLock lock(&fUncertaintyImagesMutex);
    ImageAddValue<Image>(fEventDoseImage, index, dose);
  }

  // Get information from step
  // Particle
  G4int nZ = step->GetTrack()->GetDefinition()->GetAtomicNumber();
  double kineticEnergyPerNucleon = (step->GetPreStepPoint()->GetKineticEnergy()) / (step->GetTrack()->GetDefinition()->GetAtomicMass());

  // ++_stepCount;

  // Accumulation of alpha/beta if ion type if known
  // -> check if the ion type is known
  if(fEnergyMaxForZ.count(nZ) != 0) {
    // ++_stepWithKnownIonCount;

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
    {
      G4AutoLock lock(&fDepositedMutex);
      deposited.alpha     += alpha;
      deposited.sqrtBeta  += sqrtBeta;
    }

    if(fUncertaintyFlag) {
      G4AutoLock lock(&fUncertaintyImagesMutex);

      ImageAddValue<Image>(fEventEdepImage, index, energyDep);
      ImageAddValue<Image>(fEventAlphaImage, index, alpha);
      ImageAddValue<Image>(fEventSqrtBetaImage, index, sqrtBeta);
    }

    {
      G4AutoLock lock(&fEventVoxelIndicesMutex);
      fEventVoxelIndices.insert(index);
    }
  }
}

void GateBioDoseActor::EndSimulationAction() {
  if(fUncertaintyFlag) {
    // ??
  }
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
