/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHITSPROJECTIONACTOR_H
#define OPENGATE_CORE_OPENGATEHITSPROJECTIONACTOR_H

#include "G4Cache.hh"
#include "GateHelpersHits.h"
#include "GateHitsCollection.h"
#include "GateVActor.h"
#include "itkImage.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Actor that create some projections (2D images) from several Hits Collections
 * in the same volume.
 */

class GateHitsProjectionActor : public GateVActor {

public:
  explicit GateHitsProjectionActor(py::dict &user_info);

  virtual ~GateHitsProjectionActor();

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  // Image type is 3D float by default
  typedef itk::Image<float, 3> ImageType;
  ImageType::Pointer fImage;
  std::string fPhysicalVolumeName;

protected:
  std::string fOutputFilename;
  std::vector<std::string> fInputHitsCollectionNames;
  std::vector<GateHitsCollection *> fInputHitsCollections;

  void ProcessSlice(long slice, size_t channel);

  G4ThreeVector fPreviousTranslation;
  G4RotationMatrix fPreviousRotation;

  // During computation
  struct threadLocalT {
    std::vector<std::vector<G4ThreeVector> *> fInputPos;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // OPENGATE_CORE_OPENGATEHITSPROJECTIONACTOR_H
