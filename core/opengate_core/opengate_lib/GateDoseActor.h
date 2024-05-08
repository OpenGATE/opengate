/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDoseActor_h
#define GateDoseActor_h

#include "G4Cache.hh"
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
  // explicit GateDoseActor(py::dict &user_info);
  // virtual ~GateDoseActor();

  virtual void ActorInitialize() override;

  // Main function called every step in attached volume
  virtual void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)
  virtual void BeginOfRunAction(const G4Run *run) override;

  virtual void BeginOfRunActionMasterThread(int run_id) override;

  virtual int EndOfRunActionMasterThread(int run_id) override;

  virtual void BeginOfEventAction(const G4Event *event) override;

  // virtual void EndOfEventAction(const G4Event *event) override;

  // Called every time the simulation is about to end (all threads)
  // virtual void EndOfSimulationWorkerAction(const G4Run *lastRun) override;

  // Called every time a Run ends (all threads)
  virtual void EndOfRunAction(const G4Run *run) override;

  // virtual void EndSimulationAction();

  // Image type is 3D float by default
  typedef itk::Image<float, 3> Image3DType;

  int sub2ind(Image3DType::IndexType index3D);
  void ind2sub(int index, Image3DType::IndexType &index3D);
  void ComputeSquareImage();
  double ComputeMeanUncertainty();
  double GetMaxValueOfImage(Image3DType::Pointer imageP);

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_edep_image;

  // Option: indicate if we must compute uncertainty
  bool fUncertaintyFlag;

  // Option: indicate if we must compute square
  bool fSquareFlag;

  // Option: indicate if we must compute dose in Gray also
  bool fDoseFlag;

  // Option: indicate we must convert to dose to water
  bool fToWaterFlag;

  // Option: calculate dose in stepping action. If False, calc only edep and
  // divide by masss at the end of the simulation, on py side
  bool fOnFlyCalcFlag;

  // Option: cp image for each thread
  bool fcpImageForThreadsFlag;

  // Option: calculate the standard error of the mean
  bool fSTEofMeanFlag;

  // For uncertainty computation, we need temporary images

  Image3DType::Pointer cpp_square_image;
  Image3DType::SizeType size_edep;

  double fVoxelVolume;
  int NbOfEvent = 0;
  int NbOfThreads = 0;
  double goalUncertainty;
  double threshEdepPerc;
  // struct timeval mTimeOfLastSaveEvent;

  std::string fPhysicalVolumeName;

  G4ThreeVector fInitialTranslation;
  std::string fHitType;

protected:
  struct threadLocalT {
    G4EmCalculator emcalc;
    std::vector<double> edep_worker_flatimg;
    std::vector<double> edepSquared_worker_flatimg;
    std::vector<int> lastid_worker_flatimg;
    int NbOfEvent_worker = 0;
    // Image3DType::IndexType index3D;
    // int index_flat;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDoseActor_h
