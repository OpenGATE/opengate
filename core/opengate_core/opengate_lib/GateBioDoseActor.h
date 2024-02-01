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

  void InitializeUserInput(py::dict &user_info) override;

  void InitializeCpp() override;

  void BeginOfRunActionMasterThread(int run_id) override;
  int EndOfRunActionMasterThread(int run_id) override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfEventAction(const G4Event *event) override;
  void EndOfEventAction(const G4Event *event) override;

  void EndSimulationAction() override;

	std::string GetPhysicalVolumeName() const {
		return fPhysicalVolumeName;
	}

	void SetPhysicalVolumeName(std::string s) {
		fPhysicalVolumeName = s;
	}

protected:
	void updateData();
	void loadBiophysicalModel(std::string const&);

private:
  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
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

  Image::Pointer fEdepImage;

  // Image fEventEdepImage;
  // Image fEventDoseImage;
  // Image fEventAlphaImage;
  // Image fEventSqrtBetaImage;

  int fStepCount = 0;
  int fStepWithKnownIonCount = 0;

  friend void init_GateBioDoseActor(py::module &m);
};

#endif // GateBioDoseActor_h
