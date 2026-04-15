/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiAttributeLastProcessDefinedStepInVolumeActor_h
#define GateDigiAttributeLastProcessDefinedStepInVolumeActor_h

#include "../GateHelpers.h"
#include <pybind11/stl.h>

class GateDigiAttributeLastProcessDefinedStepInVolume;

class GateDigiAttributeLastProcessDefinedStepInVolumeActor : public GateVActor {
public:
  GateDigiAttributeLastProcessDefinedStepInVolumeActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void SteppingAction(G4Step *step) override;

  void BeginOfEventAction(const G4Event *event) override;

  std::string GetLastProcess() const;
  std::string fLastProcess;
  GateDigiAttributeLastProcessDefinedStepInVolume *fAttribute;
};

#endif // GateDigiAttributeLastProcessDefinedStepInVolumeActor_h
