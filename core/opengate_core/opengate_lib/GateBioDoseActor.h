/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateBioDoseActor_h
#define GateBioDoseActor_h

#include <pybind11/stl.h>
#include <itkImage.h>

#include "GateVActor.h"

namespace py = pybind11;

class GateBioDoseActor : public GateVActor {
public:
	using Image = itk::Image<double, 3>;

	struct Coefficients {
		double a, b;
	};

	struct AlphaBetaCoefficients {
		Coefficients alpha;
		Coefficients sqrtBeta;
	};

	using VoxelIndex = Image::IndexType;
	using VoxelIndices = std::set<VoxelIndex>;

	using Fragment = std::pair<int, double>;
	using AlphaBetaInterpolTable = std::map<Fragment, AlphaBetaCoefficients>;

	using EnergyMaxForZ = std::map<int, double>;

public:
  GateBioDoseActor(py::dict &user_info);

  void ActorInitialize() override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfEventAction(const G4Event *event) override;
  void EndOfEventAction(const G4Event *event) override;

  void EndSimulationAction() override;

protected:
	void updateData();
	void loadBiophysicalModel(std::string const&);

private:
	G4Mutex fNbOfEventMutex = G4MUTEX_INITIALIZER;
	G4Mutex fDepositedMutex = G4MUTEX_INITIALIZER;
	G4Mutex fEventVoxelIndicesMutex = G4MUTEX_INITIALIZER;
	G4Mutex fUncertaintyImagesMutex = G4MUTEX_INITIALIZER;

  G4ThreeVector fInitialTranslation;
  std::string fHitType;

	int fNbOfEvent;

	EnergyMaxForZ fEnergyMaxForZ;

	std::string fDataBase;
	std::string fCellLine;
	std::string fBioPhysicalModel;
	double fAlphaRef;
	double fBetaRef;
	double fDoseScaleFactor = 1.;
	double fSOBPWeight;

	AlphaBetaInterpolTable fAlphaBetaInterpolTable;

	VoxelIndices fEventVoxelIndices;
	VoxelIndices fVoxelIndices;

	Image::Pointer fHitEventCountImage;

	Image::Pointer fEventEdepImage;
	Image::Pointer fEventDoseImage;
	Image::Pointer fEventAlphaImage;
	Image::Pointer fEventSqrtBetaImage;

	Image::Pointer fEdepImage;
	Image::Pointer fDoseImage;
	Image::Pointer fScaledDoseImage;
	Image::Pointer fAlphaMixImage;
	Image::Pointer fSqrtBetaMixImage;
	Image::Pointer fBioDoseImage;
	Image::Pointer fRBEImage;

	Image::Pointer fDoseUncertaintyImage;
	Image::Pointer fBioDoseUncertaintyImage;
	Image::Pointer fSquaredDoseImage;
	Image::Pointer fSquaredAlphaMixImage;
	Image::Pointer fSquaredSqrtBetaMixImage;
	Image::Pointer fAlphaMixSqrtBetaMixImage;
	Image::Pointer fAlphaMixDoseImage;
	Image::Pointer fSqrtBetaMixDoseImage;
	std::vector<Image::Pointer> fUncertaintyImages;

	Image::Pointer fPdBioDoseAlphaMixMean;
	Image::Pointer fPdBioDoseSqrtBetaMixMean;
	Image::Pointer fPdBioDoseDoseMean;
	Image::Pointer fVarAlphaMixMeanImage;
	Image::Pointer fVarSqrtBetaMixMeanImage;
	Image::Pointer fVarDoseMeanImage;
	Image::Pointer fCovAlphaMixMeanSqrtBetaMixMeanImage;
	Image::Pointer fCovAlphaMixMeanDoseMeanImage;
	Image::Pointer fCovSqrtBetaMixMeanDoseMeanImage;
	std::vector<Image::Pointer> fUncertaintyDetailsImages;

	bool fEdepFlag = false;
	bool fDoseFlag = false;
	bool fAlphaMixFlag = false;
	bool fSqrtBetaMixFlag = false;
	bool fRBEFlag = false;
	bool fUncertaintyFlag = false;
	bool fUncertaintyDetailsFlag = false;
	bool fHitEventCountFlag = false;

	int fStepCount = 0;
	int fStepWithKnownIonCount = 0;

	friend void init_GateBioDoseActor(py::module &m);
};

#endif // GateBioDoseActor_h
