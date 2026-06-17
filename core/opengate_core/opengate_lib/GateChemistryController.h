/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemistryController_h
#define GateChemistryController_h

#include "GateVChemistryActor.h"

class GateChemistryController : public GateVChemistryActor {

public:
  explicit GateChemistryController(py::dict &user_info);

  ~GateChemistryController() override = default;

  void InitializeUserInfo(py::dict &user_info) override;

  void StartChemistryTracking(G4Track *track) override;

protected:
  bool fConfineChemistryToVolume{false};
};

#endif // GateChemistryController_h
