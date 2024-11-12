/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEDIGITIZERPROJECTIONACTOR_H
#define OPENGATE_CORE_OPENGATEDIGITIZERPROJECTIONACTOR_H

#include "../GateVActor.h"
#include "G4Cache.hh"
#include "GateDigiCollection.h"
#include "GateHelpersDigitizer.h"
#include "itkImage.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Actor that create some projections (2D images) from several Digi Collections
 * in the same volume.
 */

class GateDigitizerProjectionActor : public GateVActor {

public:
  explicit GateDigitizerProjectionActor(py::dict &user_info);

  ~GateDigitizerProjectionActor() override;

  void InitializeUserInput(py::dict &user_info) override;

  void InitializeCpp() override;

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called every time a Run starts (master thread)
  void BeginOfRunActionMasterThread(int run_id) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  void SetPhysicalVolumeName(std::string name);

  // Image type is 3D float by default
  typedef itk::Image<float, 3> ImageType;
  ImageType::Pointer fImage;
  std::string fPhysicalVolumeName;

protected:
  std::vector<std::string> fInputDigiCollectionNames;
  std::vector<GateDigiCollection *> fInputDigiCollections;
  G4RotationMatrix fDetectorOrientationMatrix;

  void ProcessSlice(long slice, size_t channel);

  G4ThreeVector fPreviousTranslation;
  G4RotationMatrix fPreviousRotation;

  // During computation
  struct threadLocalT {
    std::vector<std::vector<G4ThreeVector> *> fInputPos;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // OPENGATE_CORE_OPENGATEDIGITIZERPROJECTIONACTOR_H
