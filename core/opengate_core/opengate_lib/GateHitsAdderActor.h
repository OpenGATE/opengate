/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsAdderActor_h
#define GateHitsAdderActor_h

#include "G4Cache.hh"
#include "GateHelpersHits.h"
#include "GateHitsCollection.h"
#include "GateHitsCollectionIterator.h"
#include "GateTHitAttribute.h"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Create a collection of "singles":
 *
 * - when every event ends, we consider all hits in the bottom most volume
 * - sum all deposited energy
 * - compute one single position, either the one the hit with the max energy
 * (EnergyWinnerPosition) or the energy weighted position
 * (EnergyWeightedCentroidPosition)
 *
 *  Warning: if the volume is composed of several sub volumes, hits will be
 *  grouped independently for all sub-volumes. This is determine thanks to the
 * UniqueVolumeID.
 *
 *  Warning: hits are gathered per Event, not per time.
 *
 */

class GateHitsAdderInVolume;

class GateHitsAdderActor : public GateVActor {

public:
  enum AdderPolicy {
    Error,
    EnergyWinnerPosition,
    EnergyWeightedCentroidPosition
  };

  explicit GateHitsAdderActor(py::dict &user_info);

  ~GateHitsAdderActor() override;

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
  AdderPolicy fPolicy;
  std::vector<std::string> fUserSkipHitAttributeNames;
  int fClearEveryNEvents;

  GateVHitAttribute *fOutputEdepAttribute;
  GateVHitAttribute *fOutputPosAttribute;
  GateVHitAttribute *fOutputGlobalTimeAttribute;

  void InitializeComputation();

  void AddHitPerVolume();

  // During computation (thread local)
  struct threadLocalT {
    std::map<GateUniqueVolumeID::Pointer, GateHitsAdderInVolume>
        fMapOfHitsInVolume;
    GateHitsAttributesFiller *fHitsAttributeFiller;
    GateHitsCollection::Iterator fInputIter;
    double *edep;
    G4ThreeVector *pos;
    GateUniqueVolumeID::Pointer *volID;
    double *time;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateHitsAdderActor_h
