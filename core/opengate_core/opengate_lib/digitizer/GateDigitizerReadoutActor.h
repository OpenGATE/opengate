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

  void StartSimulationAction() override;

  void EndOfEventAction(const G4Event *event) override;

  void SetDiscretizeVolumeDepth(int depth);

  unsigned long GetIgnoredHitsCount() const { return fIgnoredHitsCount; }

protected:
  size_t fDiscretizeVolumeDepth;
  G4Navigator *fNavigator;
  unsigned long fIgnoredHitsCount;
};

#endif // GateDigitizerDiscretizerActor_h
