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

  virtual void BeginOfEventAction(const G4Event *event);

  virtual void EndSimulationAction();

  // Image type is 3D float by default
  typedef itk::Image<float, 3> Image3DType;

  typedef itk::Image<float, 4> Image4DType;
  typedef itk::Image<int, 4> ImageInt4DType;
  using Size4DType = Image4DType::SizeType;
  Size4DType size_4D;

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_edep_image;

  // Option: indicate if we must compute uncertainty
  bool fUncertaintyFlag;

  // Option: indicate if we must compute square
  bool fSquareFlag;

  // Option: indicate if we must compute dose in Gray also
  bool fGrayFlag;

  // For uncertainty computation, we need temporary images

  Image3DType::Pointer cpp_square_image;
  Image3DType::Pointer cpp_dose_image;
  Image3DType::SizeType size_edep;

  ImageInt4DType::Pointer cpp_4D_last_id_image;
  Image4DType::Pointer cpp_4D_temp_image;
  double fVoxelVolume;
  int NbOfEvent = 0;
  int NbOfThreads = 0;

  std::string fPhysicalVolumeName;

  G4ThreeVector fInitialTranslation;
  std::string fHitType;
};

#endif // GateDoseActor_h
