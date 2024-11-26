/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateProductionAndStoppingActor_h
#define GateProductionAndStoppingActor_h

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateVActor.h"
#include "itkImage.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateProductionAndStoppingActor : public GateVActor {

public:
  // Constructor
  GateProductionAndStoppingActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  // Called every time a Run starts (all threads)

  void BeginOfRunActionMasterThread(int run_id) override;

  // Called every time a Track ends
  void PostUserTrackingAction(const G4Track *track) override;
  void AddValueToImage(const G4Step *step);

  inline std::string GetPhysicalVolumeName() const {
    return fPhysicalVolumeName;
  }

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  // Image type is 3D float by default
  // TODO double precision required
  typedef itk::Image<double, 3> ImageType;

  // The image is accessible on py side (shared by all threads)
  ImageType::Pointer cpp_value_image;

  // Option: indicate if we must compute dose in Gray also
  std::string fPhysicalVolumeName;
  std::string fMethod;
  bool fStopImageEnabled;
  bool fProductionImageEnabled;

private:
  double fVoxelVolume;

  G4ThreeVector fInitialTranslation;
  std::string fHitType;
};

#endif // GateProductionAndStoppingActor_h
