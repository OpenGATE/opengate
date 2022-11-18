/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsDiscretizerActor_h
#define GateHitsDiscretizerActor_h

#include "G4Cache.hh"
#include "GateHelpersHits.h"
#include "GateHitsCollection.h"
#include "GateHitsCollectionIterator.h"
#include "GateTHitAttribute.h"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * In a hits collection, replace the position by the center of the volume.
 * Each dimension (X,Y,Z) can be independently discretized or not
 */

class GateHitsAdderInVolume;

class GateHitsDiscretizerActor : public GateVActor {

public:
  explicit GateHitsDiscretizerActor(py::dict &user_info);

  ~GateHitsDiscretizerActor() override;

  // to set parameters computed from python side
  void SetVolumeDepth(int depth_x, int depth_y, int depth_z);

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called when the simulation end (master thread only)
  void EndSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event starts
  void BeginOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  void EndOfSimulationWorkerAction(const G4Run * /*unused*/) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

protected:
  std::string fOutputFilename;
  std::string fInputHitsCollectionName;
  std::string fOutputHitsCollectionName;
  GateHitsCollection *fOutputHitsCollection;
  GateHitsCollection *fInputHitsCollection;
  int fClearEveryNEvents;
  int fDepthX;
  int fDepthY;
  int fDepthZ;

  GateVHitAttribute *fOutputPosAttribute{};

  void InitializeComputation();

  // During computation (thread local)
  struct threadLocalT {
    GateHitsAttributesFiller *fHitsAttributeFiller;
    GateHitsCollection::Iterator fInputIter;
    G4ThreeVector *pos;
    GateUniqueVolumeID::Pointer *volID;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateHitsDiscretizerActor_h
