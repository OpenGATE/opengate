/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateFluenceActor_h
#define GateFluenceActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateVActor.h"
#include "digitizer/GateDigiAttributeLastProcessDefinedStepInVolumeActor.h"
#include "itkImage.h"
#include <iostream>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateFluenceActor : public GateVActor {

public:
  // Constructor
  GateFluenceActor(py::dict &user_info);

  void InitializeCpp() override;
  void InitializeUserInfo(py::dict &user_info) override;
  void StartSimulationAction() override;
  void BeginOfEventAction(const G4Event *event) override;
  void SteppingAction(G4Step *) override;
  void BeginOfRunActionMasterThread(int run_id) override;
  void BeginOfRunAction(const G4Run *run) override;
  void EndOfRunAction(const G4Run *run) override;

  inline std::string GetPhysicalVolumeName() { return fPhysicalVolumeName; }
  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  int fNbOfEvent = 0;

  // Image type is 3D float by default
  typedef itk::Image<float, 3> Image3DType;
  typedef itk::Image<float, 4> Image4DType;
  typedef itk::Image<int, 4> ImageInt4DType;
  using Size4DType = Image4DType::SizeType;
  Size4DType size_4D;

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_counts_image;
  Image3DType::Pointer cpp_counts_compton_image;
  Image3DType::Pointer cpp_counts_rayleigh_image;
  Image3DType::Pointer cpp_counts_secondaries_image;
  Image3DType::Pointer cpp_counts_primaries_image;

  Image3DType::Pointer cpp_energy_image;
  Image3DType::Pointer cpp_energy_compton_image;
  Image3DType::Pointer cpp_energy_rayleigh_image;
  Image3DType::Pointer cpp_energy_secondaries_image;
  Image3DType::Pointer cpp_energy_primaries_image;

  Image3DType::Pointer cpp_counts_squared_image;
  Image3DType::Pointer cpp_counts_squared_compton_image;
  Image3DType::Pointer cpp_counts_squared_rayleigh_image;
  Image3DType::Pointer cpp_counts_squared_secondaries_image;
  Image3DType::Pointer cpp_counts_squared_primaries_image;

  Image3DType::Pointer cpp_energy_squared_image;
  Image3DType::Pointer cpp_energy_squared_compton_image;
  Image3DType::Pointer cpp_energy_squared_rayleigh_image;
  Image3DType::Pointer cpp_energy_squared_secondaries_image;
  Image3DType::Pointer cpp_energy_squared_primaries_image;

  Image3DType::SizeType size_region{};

  struct threadLocalT {
    G4EmCalculator emcalc;
    std::vector<double> squared_worker_flatimg;
    std::vector<int> lastid_worker_flatimg;
  };

  G4Cache<threadLocalT> fThreadLocalDataCounts;
  G4Cache<threadLocalT> fThreadLocalDataComptCounts;
  G4Cache<threadLocalT> fThreadLocalDataRaylCounts;
  G4Cache<threadLocalT> fThreadLocalDataSecCounts;
  G4Cache<threadLocalT> fThreadLocalDataPrimCounts;
  G4Cache<threadLocalT> fThreadLocalDataEnergy;
  G4Cache<threadLocalT> fThreadLocalDataComptEnergy;
  G4Cache<threadLocalT> fThreadLocalDataRaylEnergy;
  G4Cache<threadLocalT> fThreadLocalDataSecEnergy;
  G4Cache<threadLocalT> fThreadLocalDataPrimEnergy;

  G4bool fCountsSquaredFlag;
  G4bool fEnergyFlag;
  G4bool fEnergySquaredFlag;
  G4bool fSecondaries;
  GateDigiAttributeLastProcessDefinedStepInVolumeActor *fLastProcessActor;

  void FlushSquaredValues(threadLocalT &data,
                          const Image3DType::Pointer &cpp_image);
  void ScoreSquaredValue(threadLocalT &data,
                         const Image3DType::Pointer &cpp_image,
                         const double value, const int event_id,
                         const Image3DType::IndexType &index);
  int sub2ind(Image3DType::IndexType index3D);
  void PrepareLocalDataForRun(threadLocalT &data,
                              const unsigned int numberOfVoxels);

  bool GetEnergySquaredFlag() const { return fEnergySquaredFlag; }
  void SetEnergySquaredFlag(const bool b) { fEnergySquaredFlag = b; }
  void SetEnergyFlag(const bool b) { fEnergyFlag = b; }
  bool GetEnergyFlag() const { return fEnergyFlag; }
  void SetCountsSquaredFlag(const bool b) { fCountsSquaredFlag = b; }
  bool GetCountsSquaredFlag() const { return fCountsSquaredFlag; }

protected:
  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
  std::string fHitType;
};

#endif // GateFluenceActor_h
