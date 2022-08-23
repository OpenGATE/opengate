/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDoseActor_h
#define GateDoseActor_h

#include "G4VPrimitiveScorer.hh"
#include "GateVActor.h"
#include "itkImage.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateDoseActor : public GateVActor {

public:
  // Constructor
  GateDoseActor(py::dict &user_info);

  virtual void ActorInitialize();

  // Main function called every step in attached volume
  virtual void SteppingAction(G4Step *);

  // Called every time a Run starts (all threads)
  virtual void BeginOfRunAction(const G4Run *run);

  virtual void EndSimulationAction();

  // Image type is 3D float by default
  typedef itk::Image<float, 3> ImageType;

  // The image is accessible on py side (shared by all threads)
  ImageType::Pointer cpp_edep_image;

  // Option: indicate if we must compute uncertainty
  bool fUncertaintyFlag;

  // Option: indicate if we must compute dose in Gray also
  bool fGrayFlag;

  // For uncertainty computation, we need temporary images
  ImageType::Pointer cpp_square_image;
  ImageType::Pointer cpp_temp_image;
  ImageType::Pointer cpp_last_id_image;
  ImageType::Pointer cpp_dose_image;
  double fVoxelVolume;

  std::string fPhysicalVolumeName;

  G4ThreeVector fInitialTranslation;
  std::string fHitType;
};

#endif // GateDoseActor_h
