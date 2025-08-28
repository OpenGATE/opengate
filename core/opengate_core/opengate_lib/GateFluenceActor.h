/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateFluenceActor_h
#define GateFluenceActor_h

#include "GateDoseActor.h"
#include "GateMaterialMuHandler.h"

#include "G4Cache.hh"
#include "G4EmCalculator.hh"
#include "G4NistManager.hh"
#include "G4VPrimitiveScorer.hh"

#include <iostream>
#include <pybind11/stl.h>

#include "GateVActor.h"
#include "itkImage.h"
#include <G4Threading.hh>

#include <itkCastImageFilter.h>
#include <itkImageFileWriter.h>

namespace py = pybind11;

class GateFluenceActor : public GateVActor {

public:
  // Constructor
  GateFluenceActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  void BeginOfRunActionMasterThread(int run_id) override;

  void BeginOfEventAction(const G4Event *event) override;

  int EndOfRunActionMasterThread(int run_id) override;

  void EndOfRunAction(const G4Run *run) override;

  std::string GetOutputImage();

  // Main function called every step in attached volume
  void SteppingAction(G4Step *) override;

  inline std::string GetPhysicalVolumeName() const {
    return fPhysicalVolumeName;
  }

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  std::string fPhysicalVolumeName;

  typedef itk::Image<double, 3> Image3DType;
  Image3DType::Pointer tof_cpp_image;
  typedef itk::Image<double, 2> Image2DType;
  Image2DType::Pointer output_image;

  G4ThreeVector fTranslation;
  G4ThreeVector fsize;
  G4ThreeVector fspacing;

private:
  G4int norm;
  G4int nb_inel;
  G4int Nbbinstime;
  G4int Nbbinsenergy;
  G4double creationtime;
  std::string foutputname;
};

#endif // GateFluenceActor_h
