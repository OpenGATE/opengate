/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiAttributeLastProcessDefinedStepInVolume_h
#define GateDigiAttributeLastProcessDefinedStepInVolume_h

#include "../GateHelpers.h"
#include "GateTDigiAttribute.h"
#include <pybind11/stl.h>

#include "GateDigiAttributeLastProcessDefinedStepInVolumeActor.h"

class GateDigiAttributeLastProcessDefinedStepInVolume
    : public GateTDigiAttribute<std::string> {
public:
  GateDigiAttributeLastProcessDefinedStepInVolume(
      const std::string &att_name,
      const GateDigiAttributeLastProcessDefinedStepInVolumeActor *actor);

  std::string GetProcessDefinedStepInVolume(const G4Step *step) const;

  const GateDigiAttributeLastProcessDefinedStepInVolumeActor *fActor;
};

#endif // GateDigiAttributeLastProcessDefinedStepInVolume_h
