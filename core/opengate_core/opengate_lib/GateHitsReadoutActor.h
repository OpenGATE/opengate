/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsDiscretizerActor_h
#define GateHitsDiscretizerActor_h

#include "G4Cache.hh"
#include "GateVActor.h"
#include "digitizer/GateDigiCollection.h"
#include "digitizer/GateDigiCollectionIterator.h"
#include "digitizer/GateDigitizerAdderActor.h"
#include "digitizer/GateHelpersDigitizer.h"
#include "digitizer/GateTDigiAttribute.h"
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

class GateHitsReadoutActor : public GateDigitizerAdderActor {

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
