/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateWeightedEdepActor_h
#define GateWeightedEdepActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateVActor.h"
#include "itkImage.h"
#include <pybind11/stl.h>
#include "GateHelpersImage.h"

namespace py = pybind11;

class GateWeightedEdepActor : public GateVActor {

public:

  // Image type is 3D float by default
  // TODO double precision required
  typedef itk::Image<double, 3> ImageType;

  // Constructor
  GateWeightedEdepActor(py::dict &user_info);

  virtual void InitializeUserInput(py::dict &user_info) override;

  virtual void InitializeCpp() override;

  // Main function called every step in attached volume
  virtual void SteppingAction(G4Step *) override;

  virtual void BeginOfEventAction(const G4Event *event) override;

  // Called every time a Run starts (all threads)
  virtual void BeginOfRunAction(const G4Run *run) override;

  virtual void BeginOfRunActionMasterThread(int run_id) override;

  virtual void EndSimulationAction() override;
  
  virtual void AddValuesToImages(G4Step *step, ImageType::IndexType index);

  inline std::string GetPhysicalVolumeName() const {
    return fPhysicalVolumeName;
  }

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  // The image is accessible on py side (shared by all threads)
  ImageType::Pointer cpp_numerator_image;
  ImageType::Pointer cpp_denominator_image;

  // Option: indicate if we must compute dose in Gray also
  std::string fPhysicalVolumeName;
  std::string fScoreIn;
//   bool fdoseAverage;
//   bool ftrackAverage;
//   bool fLETtoOtherMaterial;
  std::string fotherMaterial;

  int NbOfEvent = 0;

protected:
  double fVoxelVolume;

  G4ThreeVector fInitialTranslation;
  std::string fHitType;

  bool fScoreInOtherMaterial = false;

  struct threadLocalT {
    G4EmCalculator emcalc;
    G4Material *materialToScoreIn;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateWeightedEdepActor_h
