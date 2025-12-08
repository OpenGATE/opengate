/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDoseActor_h
#define GateDoseActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateVActor.h"
#include "itkImage.h"

namespace py = pybind11;

class GateDoseActor : public GateVActor {

public:
  // Constructor
  explicit GateDoseActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  // The main function called every step in the attached volume
  void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  int EndOfRunActionMasterThread(int run_id) override;

  void BeginOfEventAction(const G4Event *event) override;

  void EndOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  bool GetToWaterFlag() const { return fToWaterFlag; }

  void SetToWaterFlag(const bool b) { fToWaterFlag = b; }

  bool GetEdepSquaredFlag() const { return fEdepSquaredFlag; }

  void SetEdepSquaredFlag(const bool b) { fEdepSquaredFlag = b; }

  void SetDoseFlag(const bool b) { fDoseFlag = b; }

  bool GetDoseFlag() const { return fDoseFlag; }

  void SetDoseSquaredFlag(const bool b) { fDoseSquaredFlag = b; }

  bool GetDoseSquaredFlag() const { return fDoseSquaredFlag; }

  void SetCountsFlag(const bool b) { fCountsFlag = b; }

  bool GetCountsFlag() const { return fCountsFlag; }

  void SetUncertaintyGoal(const double b) { fUncertaintyGoal = b; }

  void SetThreshEdepPerc(const double b) { fThreshEdepPerc = b; }

  void SetOvershoot(const double b) { fOvershoot = b; }

  void SetNbEventsFirstCheck(const int b) { fNbEventsFirstCheck = b; }

  std::string GetPhysicalVolumeName() const { return fPhysicalVolumeName; }

  void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  // Image type needs to be 3D double by default
  typedef itk::Image<double, 3> Image3DType;

  int sub2ind(Image3DType::IndexType index3D);

  void ind2sub(int index, Image3DType::IndexType &index3D);

  double GetMaxValueOfImage(Image3DType::Pointer imageP);
  double ComputeMeanUncertainty();

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_edep_image;
  Image3DType::Pointer cpp_edep_squared_image;
  Image3DType::Pointer cpp_dose_image;
  Image3DType::Pointer cpp_dose_squared_image;
  Image3DType::Pointer cpp_density_image;
  Image3DType::Pointer cpp_counts_image;
  Image3DType::SizeType size_edep{};

  struct threadLocalT {
    G4EmCalculator emcalc;
    std::vector<double> squared_worker_flatimg;
    std::vector<int> lastid_worker_flatimg;
  };

  void ScoreSquaredValue(threadLocalT &data,
                         const Image3DType::Pointer &cpp_image, double value,
                         int event_id, const Image3DType::IndexType &index);

  void FlushSquaredValues(threadLocalT &data,
                          const Image3DType::Pointer &cpp_image);

  static void PrepareLocalDataForRun(threadLocalT &data,
                                     unsigned int numberOfVoxels);

  void GetVoxelPosition(G4Step *step, G4ThreeVector &position, bool &isInside,
                        Image3DType::IndexType &index) const;

  // Option: indicate we must convert to dose to water
  bool fToWaterFlag{};

  // Option: indicate if we must compute edep squared
  bool fEdepSquaredFlag{};

  // Option: Is the dose to be scored?
  bool fDoseFlag{};
  bool fDoseSquaredFlag{};

  // Option: Are counts to be scored
  bool fCountsFlag{};

  double fVoxelVolume{};

  // Option: set target statistical uncertainty for each run
  double fUncertaintyGoal;
  double fThreshEdepPerc;
  double fOvershoot;

  int fNbOfEvent;
  // set from python's side. It will be overwritten by an estimation of the
  // number of events needed to achieve the goal uncertainty.
  int fNbEventsFirstCheck;
  int fNbEventsNextCheck;
  double fGoalUncertainty;

  std::string fPhysicalVolumeName;

  G4ThreeVector fTranslation;
  std::string fHitType;

protected:
  G4Cache<threadLocalT> fThreadLocalDataEdep;
  G4Cache<threadLocalT> fThreadLocalDataDose;
};

#endif // GateDoseActor_h
