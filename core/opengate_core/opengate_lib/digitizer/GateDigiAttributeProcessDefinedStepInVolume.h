/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiAttributeProcessDefinedStepInVolume_h
#define GateDigiAttributeProcessDefinedStepInVolume_h

#include "../GateHelpers.h"
#include "GateTDigiAttribute.h"
#include <pybind11/stl.h>

#include "GateDigiAttributeProcessDefinedStepInVolumeActor.h"

class GateDigiAttributeProcessDefinedStepInVolume
    : public GateTDigiAttribute<int> {
public:
  GateDigiAttributeProcessDefinedStepInVolume(
      const std::string &att_name,
      const GateDigiAttributeProcessDefinedStepInVolumeActor *actor);

  int GetProcessDefinedStepInVolume(const G4Step *step) const;

  const GateDigiAttributeProcessDefinedStepInVolumeActor *fActor;
};

#endif // GateDigiAttributeProcessDefinedStepInVolume_h
