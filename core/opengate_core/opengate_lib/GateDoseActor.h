/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDoseActor_h
#define GateDoseActor_h

#include "G4Cache.hh"
#include <G4Threading.hh>
#include "G4VPrimitiveScorer.hh"
#include "GateVActor.h"
#include "itkImage.h"
#include <iostream>
#include <pybind11/stl.h>

#include "G4EmCalculator.hh"
#include "G4NistManager.hh"

namespace py = pybind11;

class GateDoseActor : public GateVActor {

public:
  // Constructor
  GateDoseActor(py::dict &user_info);

  void InitializeUserInput(py::dict &user_info) override;

  void InitializeCpp() override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  int EndOfRunActionMasterThread(int run_id) override;

  void BeginOfEventAction(const G4Event *event) override;
  
  void EndOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  inline bool GetToWaterFlag() const { return fToWaterFlag; }

  inline void SetToWaterFlag(const bool b) { fToWaterFlag = b; }

  inline bool GetSquareFlag() const { return fSquareFlag; }

  inline void SetSquareFlag(const bool b) { fSquareFlag = b; }

  inline void SetDensityFlag(const bool b) { fDensityFlag = b; }

  inline bool GetDensityFlag() const { return fDensityFlag; }

  inline std::string GetPhysicalVolumeName() const {
    return fPhysicalVolumeName;
  }

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  // virtual void EndSimulationAction();

  // Image type needs to be 3D double by default
  typedef itk::Image<double, 3> Image3DType;

  int sub2ind(Image3DType::IndexType index3D);
  void ind2sub(int index, Image3DType::IndexType &index3D);
  double ComputeMeanUncertainty();
  double GetMaxValueOfImage(Image3DType::Pointer imageP);

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_edep_image;
  //  Image3DType::Pointer cpp_dose_image;
  Image3DType::Pointer cpp_square_image;
  Image3DType::SizeType size_edep{};
  Image3DType::Pointer cpp_density_image;

  //  // Option: indicate if we must compute uncertainty
  //  bool fUncertaintyFlag;

  // Option: indicate if we must compute square
  bool fSquareFlag{};

  //  // Option: indicate if we must compute dose in Gray also
  //  bool fDoseFlag;

  std::string fScoreIn;

  // Option: indicate we must convert to dose to water
  bool fToWaterFlag{};

  // Option: indicate the density is needed
  bool fDensityFlag{};

  //  // Option: calculate dose in stepping action. If False, calc only edep and
  //  // divide by mass at the end of the simulation, on py side
  //  bool fOnFlyCalcFlag;

  //  // Option: cp image for each thread
  //  bool fcpImageForThreadsFlag;
  //
  //  // Option: calculate the standard error of the mean
  //  bool fSTEofMeanFlag;

  // For uncertainty computation, we need temporary images

  double fVoxelVolume{};
  int NbOfEvent = 0;
  int NbEventsNextCheck = 100; //we need at least some events to be able to estimate uncertainty
  int NbOfThreads = 0;

  //bool fStopRunFlag = false;
  double goalUncertainty;
  double threshEdepPerc{};
  // struct timeval mTimeOfLastSaveEvent;

  std::string fPhysicalVolumeName;

  G4ThreeVector fTranslation;
  std::string fHitType;

protected:
  struct threadLocalT {
    G4EmCalculator emcalc;
    std::vector<double> edep_worker_flatimg;
    std::vector<double> edepSquared_worker_flatimg;
    std::vector<int> lastid_worker_flatimg;
    //    int NbOfEvent_worker = 0;
    // Image3DType::IndexType index3D;
    // int index_flat;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDoseActor_h
