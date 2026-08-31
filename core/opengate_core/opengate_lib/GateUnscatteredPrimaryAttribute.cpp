/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUnscatteredPrimaryAttribute.h"
#include "digitizer/GateDigiAttributeManager.h"
#include "filters/GatePrimaryScatterFilter.h"

GateUnscatteredPrimaryAttribute::GateUnscatteredPrimaryAttribute(
    py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fDigiAttributeType = 'I';
}

void GateUnscatteredPrimaryAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();

  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    att->FillIValue(GetIValue(step));
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

int GateUnscatteredPrimaryAttribute::GetIValue(const G4Step *step) const {
  return IsUnscatteredPrimary(step);
}
