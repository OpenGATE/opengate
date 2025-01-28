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
#include "GateHelpersImage.h"
#include "GateVActor.h"
#include "itkImage.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateWeightedEdepActor : public GateVActor {

public:
  // Image type is 3D float by default
  // TODO double precision required
  typedef itk::Image<double, 3> Image3DType;

  // Constructor
  GateWeightedEdepActor(py::dict &user_info);

  virtual void InitializeUserInfo(py::dict &user_info) override;

  virtual void InitializeCpp() override;

  // Main function called every step in attached volume
  virtual void SteppingAction(G4Step *) override;

  virtual void BeginOfEventAction(const G4Event *event) override;

  // Called every time a Run starts (all threads)
  virtual void BeginOfRunAction(const G4Run *run) override;

  virtual void BeginOfRunActionMasterThread(int run_id) override;

  virtual void EndSimulationAction() override;

  inline std::string GetPhysicalVolumeName() const {
    return fPhysicalVolumeName;
  }

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  void GetVoxelPosition(G4Step *step, G4ThreeVector &position, bool &isInside,
                        Image3DType::IndexType &index) const;

  G4double GetMeanEnergy(G4Step *step);
  G4double GetCurrentDEDX(G4Step *step);
  G4double GetSPROtherMaterial(G4Step *step);

  virtual double ScoringQuantityFn(G4Step *step, double *secondQuantity);

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_numerator_image;
  Image3DType::Pointer cpp_denominator_image;
  // we need an extra image for beta scoring (lemI lda)
  Image3DType::Pointer cpp_second_numerator_image;

  bool doTrackAverage = false;  // track vs dose averaging
  bool multipleScoring = false; // do we want a second weighted image?

  // Option: indicate if we must compute dose in Gray also
  std::string fPhysicalVolumeName;
  std::string fScoreIn;
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
    G4double energy_mean;
    G4double dedx_currstep;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateWeightedEdepActor_h
