/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSteppingAction_h
#define GateSteppingAction_h

#include "G4UserSteppingAction.hh"
#include "GateVAuxiliaryAttribute.h"
#include <vector>

class GateSteppingAction : public G4UserSteppingAction {

public:
  GateSteppingAction();
  ~GateSteppingAction() override = default;

  void RegisterAuxiliaryAttribute(GateVAuxiliaryAttribute *attribute);

  void UserSteppingAction(const G4Step *step) override;

protected:
  std::vector<GateVAuxiliaryAttribute *> fSteppingActionAttributes;
};

#endif // GateSteppingAction_h
