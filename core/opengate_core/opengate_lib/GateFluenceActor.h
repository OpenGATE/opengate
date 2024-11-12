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

  void InitializeCpp() override;

  void InitializeUserInput(py::dict &user_info) override;

  // Function called every step in attached volume
  // This where the scoring takes place
  void SteppingAction(G4Step *) override;

  void BeginOfEventAction(const G4Event *event) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  inline std::string GetPhysicalVolumeName() { return fPhysicalVolumeName; }

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  int NbOfEvent = 0;

  // Image type is 3D float by default
  typedef itk::Image<float, 3> Image3DType;
  typedef itk::Image<float, 4> Image4DType;
  typedef itk::Image<int, 4> ImageInt4DType;
  using Size4DType = Image4DType::SizeType;
  Size4DType size_4D;

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_fluence_image;

private:
  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
  std::string fHitType;
};

#endif // GateFluenceActor_h
