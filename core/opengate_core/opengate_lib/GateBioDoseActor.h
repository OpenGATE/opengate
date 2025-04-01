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

  using ItkVoxelIndex = Image::IndexType;
  using ItkVoxelIndices = std::set<ItkVoxelIndex>;

  using VoxelIndex = std::array<long, 3>;
  using VoxelIndices = std::set<VoxelIndex>;

  using Fragment = std::pair<int, double>;
  using AlphaBetaInterpolTable = std::map<Fragment, AlphaBetaCoefficients>;

  using EnergyMaxForZ = std::map<int, double>;

  static VoxelIndex arrayFromItkIndex(ItkVoxelIndex const& idx) {
    return {idx[0], idx[1], idx[2]};
  }

  static ItkVoxelIndex itkIndexFromArray(VoxelIndex const& idx) {
    return {idx[0], idx[1], idx[2]};
  }

public:
  explicit GateBioDoseActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

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

  // TODO https://pybind11.readthedocs.io/en/stable/advanced/cast/custom.html
  // add a custom type_caster for itk::Index<n>
  // and remove this function and its consequences
  std::vector<VoxelIndex> GetVoxelIndicesAsVector() const {
    std::vector<VoxelIndex> v(fVoxelIndices.size());
    std::copy(std::begin(fVoxelIndices), std::end(fVoxelIndices), std::begin(v));
    return v;
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
  double fAlphaRef = 0;
  double fBetaRef = 0;
  double fDoseScaleFactor = 1.;
  double fSOBPWeight;

  AlphaBetaInterpolTable fAlphaBetaInterpolTable;

  ItkVoxelIndices fEventVoxelIndices;
  VoxelIndices fVoxelIndices;

  // from Python
  Image::Pointer fHitEventCountImage;
  Image::Pointer fEdepImage;
  Image::Pointer fDoseImage;
  Image::Pointer fAlphaMixImage;
  Image::Pointer fSqrtBetaMixImage;
  Image::Pointer fAlphaMixDoseImage;
  Image::Pointer fSqrtBetaMixDoseImage;

  Image::Pointer fSumAlphaMixImage;
  Image::Pointer fSumSqrtBetaMixImage;
  Image::Pointer fSumAlphaMixDoseImage;
  Image::Pointer fSumSqrtBetaMixDoseImage;

  // only C++-side
  Image::Pointer fEventEdepImage;
  Image::Pointer fEventDoseImage;
  Image::Pointer fEventSumAlphaMixDoseImage;
  Image::Pointer fEventSumSqrtBetaMixDoseImage;

  // metadata
  double fVoxelVolume = 0;

  int fStepCount = 0;
  int fStepWithKnownIonCount = 0;

  friend void init_GateBioDoseActor(py::module &m);
};

#endif // GateBioDoseActor_h
