/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiAttributeProcessDefinedStepInVolumeActor_h
#define GateDigiAttributeProcessDefinedStepInVolumeActor_h

#include "../GateHelpers.h"
#include <pybind11/stl.h>

class GateDigiAttributeProcessDefinedStepInVolume;

class GateDigiAttributeProcessDefinedStepInVolumeActor : public GateVActor {
public:
  GateDigiAttributeProcessDefinedStepInVolumeActor(py::dict &user_info);

  void InitializeUserInfo(py::dict &user_info) override;

  void SteppingAction(G4Step *step) override;

  void BeginOfEventAction(const G4Event *event) override;

  int GetNumberOfInteractions() const;

  std::string fProcessName;
  int fNumberOfInteractions;
  GateDigiAttributeProcessDefinedStepInVolume *fAttribute;
};

#endif // GateDigiAttributeProcessDefinedStepInVolumeActor_h
