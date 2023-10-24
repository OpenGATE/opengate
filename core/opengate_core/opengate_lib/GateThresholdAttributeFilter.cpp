/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateThresholdAttributeFilter.h"
#include "G4UnitsTable.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"

GateThresholdAttributeFilter::GateThresholdAttributeFilter() : GateVFilter() {}

void GateThresholdAttributeFilter::Initialize(py::dict &user_info) {
  fAttributeName = DictGetStr(user_info, "attribute");
  fValueMin = DictGetDouble(user_info, "value_min");
  fValueMax = DictGetDouble(user_info, "value_max");
  fFilterName = DictGetStr(user_info, "_name");
  fPolicy = DictGetStr(user_info, "policy");
  if (fPolicy == "keep")
    fKeep = true;
  else if (fPolicy == "discard")
    fKeep = false;
  else {
    std::ostringstream oss;
    oss << "Error policy must be 'keep' or 'discard' for the filter "
        << fFilterName << " while it is " << fPolicy;
    Fatal(oss.str());
  }

  auto *dgm = GateDigiAttributeManager::GetInstance();
  auto *att = dgm->GetDigiAttribute(fAttributeName);
  auto *vatt = dgm->CopyDigiAttribute(att);
  if (vatt->GetDigiAttributeType() != 'D') {
    std::ostringstream oss;
    oss << "Error the type of the attribute " << vatt->GetDigiAttributeName()
        << " must be 'D', while it is " << vatt->GetDigiAttributeType();
    Fatal(oss.str());
  }
  fAttribute = dynamic_cast<GateTDigiAttribute<double> *>(vatt);
}

bool GateThresholdAttributeFilter::Accept(const G4Track *track) const {
  return true;
}

bool GateThresholdAttributeFilter::Accept(G4Step *step) const {
  fAttribute->ProcessHits(step);
  double value = fAttribute->GetDValues()[0];
  fAttribute->Clear();
  if (value >= fValueMin && value <= fValueMax)
    return fKeep;
  return !fKeep;
}
