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
#include "GateHitsAdderActor.h"
#include "GateHitsCollection.h"
#include "GateHitsCollectionIterator.h"
#include "GateTHitAttribute.h"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Create a collection of "Singles". Perform a GateHitsAdderActor +
 * discretization of the final position.
 *
 * The final position is computed according to the center of the given volume
 *
 */

class GateHitsAdderInVolume;

class GateHitsReadoutActor : public GateHitsAdderActor {

public:
  explicit GateHitsReadoutActor(py::dict &user_info);

  ~GateHitsReadoutActor() override;

  void StartSimulationAction() override;

  void EndOfEventAction(const G4Event *event) override;

  void SetDiscretizeVolumeDepth(int depth);

protected:
  int fDiscretizeVolumeDepth;
  G4Navigator *fNavigator;
  G4TouchableHistory fTouchableHistory;
};

#endif // GateHitsDiscretizerActor_h
