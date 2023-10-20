/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerDiscretizerActor_h
#define GateDigitizerDiscretizerActor_h

#include "../GateVActor.h"
#include "G4Cache.hh"
#include "G4Navigator.hh"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionIterator.h"
#include "GateDigitizerAdderActor.h"
#include "GateHelpersDigitizer.h"
#include "GateTDigiAttribute.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Create a collection of "Singles". Perform a GateDigitizerAdderActor +
 * discretization of the final position.
 *
 * The final position is computed according to the center of the given volume
 *
 */

class GateDigiAdderInVolume;

class GateDigitizerReadoutActor : public GateDigitizerAdderActor {

public:
  explicit GateDigitizerReadoutActor(py::dict &user_info);

  ~GateDigitizerReadoutActor() override;

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event ends
  void EndOfEventAction(const G4Event *event) override;

  // Called by every worker when the simulation is about to end
  // (after last run)
  void EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) override;

  void SetDiscretizeVolumeDepth(int depth);

  unsigned long GetIgnoredHitsCount() const { return fIgnoredHitsCount; }

protected:
  size_t fDiscretizeVolumeDepth;
  unsigned long fIgnoredHitsCount; // global instance

  struct threadLocalReadoutT {
    G4Navigator *fNavigator = nullptr;
    unsigned long fIgnoredHitsCount; // thread local instance
  };
  G4Cache<threadLocalReadoutT> fThreadLocalReadoutData;
};

#endif // GateDigitizerDiscretizerActor_h
