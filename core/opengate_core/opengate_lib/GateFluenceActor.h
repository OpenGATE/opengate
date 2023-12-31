/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateFluenceActor_h
#define GateFluenceActor_h

#include "G4Cache.hh"
#include "G4VPrimitiveScorer.hh"
#include "GateVActor.h"
#include "itkImage.h"
#include <iostream>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateFluenceActor : public GateVActor {

public:
  // Constructor
  GateFluenceActor(py::dict &user_info);

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
  Image3DType::Pointer cpp_fluence_image;
  Image3DType::SizeType size_fluence;
  double fVoxelVolume;
  int NbOfThreads = 0;

  std::string fPhysicalVolumeName;

  G4ThreeVector fInitialTranslation;
  std::string fHitType;
};

#endif // GateFluenceActor_h
