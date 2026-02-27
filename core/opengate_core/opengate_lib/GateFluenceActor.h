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

  void InitializeUserInfo(py::dict &user_info) override;

  // Function called every step in attached volume
  // This where the scoring takes place
  void SteppingAction(G4Step *) override;

  void BeginOfEventAction(const G4Event *event) override;

  void BeginOfRunActionMasterThread(int run_id) override;

  inline std::string GetPhysicalVolumeName() { return fPhysicalVolumeName; }

  inline void SetPhysicalVolumeName(std::string s) { fPhysicalVolumeName = s; }

  // Image type is 3D float by default
  void SetSumTracksFlag(const bool b) { fSumTracksFlag = b; }

  bool GetSumTracksFlag() const { return fSumTracksFlag; }

  // Set the fluence scoring mode
  inline void SetFluenceScoringMode(std::string mode) {
    fFluenceScoringMode = mode;
  }

  inline std::string GetFluenceScoringMode() const {
    return fFluenceScoringMode;
  }

  int NbOfEvent = 0;

  // Image type is 3D float by default
  typedef itk::Image<float, 3> Image3DType;
  typedef itk::Image<float, 4> Image4DType;
  typedef itk::Image<int, 4> ImageInt4DType;
  using Size4DType = Image4DType::SizeType;
  Size4DType size_4D;

  void GetVoxelPosition(G4Step *step, G4ThreeVector &position, bool &isInside,
                        Image3DType::IndexType &index,
                        Image3DType::Pointer &image) const;

  // The image is accessible on py side (shared by all threads)
  Image3DType::Pointer cpp_fluence_image;
  Image3DType::Pointer cpp_fluence_sum_tracks_image;

  // Option: Is the fluence as sum of the tracks to be scored?
  bool fSumTracksFlag{};

  // store the voexl volume for later use (for example to compute dose from
  // fluence)
  double fVoxelVolume{};

private:
  std::string fPhysicalVolumeName;
  G4ThreeVector fTranslation;
  std::string fHitType;
  std::string fFluenceScoringMode = "sum_tracks";
};

#endif // GateFluenceActor_h
