/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateKineticEnergyFilter.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

void GateKineticEnergyFilter::Initialize(py::dict &user_info) {
  fEnergyMin = DictGetDouble(user_info, "energy_min");
  fEnergyMax = DictGetDouble(user_info, "energy_max");
}

bool GateKineticEnergyFilter::Accept(G4Step *step) const {
  auto e = step->GetPreStepPoint()->GetKineticEnergy();
  if (e < fEnergyMin)
    return false;
  if (e > fEnergyMax)
    return false;
  return true;
}
