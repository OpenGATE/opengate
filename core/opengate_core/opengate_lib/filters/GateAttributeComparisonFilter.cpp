/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAttributeComparisonFilter.h"

// Explicitly instantiate the numeric types
template class GateAttributeComparisonFilter<double>;
template class GateAttributeComparisonFilter<int>;
// template class GateAttributeComparisonFilter<G4ThreeVector>; NOT YET

// Specialization for String ("contains" logic)
template <>
void GateAttributeComparisonFilter<std::string>::InitializeUserInfo(
    py::dict &user_info) {
  fAttributeName = DictGetStr(user_info, "attribute");
  fValueMin =
      DictGetStr(user_info, "value_min"); // Use "value" as the search string

  // search mode: "contains" or "equal" or "start"
  fSearchMode =
      user_info.contains("mode") ? DictGetStr(user_info, "mode") : "equal";

  auto *dgm = GateDigiAttributeManager::GetInstance();
  auto *att = dgm->GetDigiAttribute(fAttributeName);
  fAttribute = dynamic_cast<GateTDigiAttribute<std::string> *>(
      dgm->CopyDigiAttribute(att));
  fAttribute->SetSingleValueMode(true);
}

// Specialised implementation for std::string (Equality instead of Range)
template <>
bool GateAttributeComparisonFilter<std::string>::Accept(G4Step *step) const {
  fAttribute->ProcessHits(step);
  const auto val = fAttribute->GetSingleValue();
  bool result = false;

  if (fSearchMode == "equal") {
    result = (val == fValueMin);
  } else if (fSearchMode == "contains") {
    result = (val.find(fValueMin) != std::string::npos);
  } else if (fSearchMode == "start") {
    result = (val.rfind(fValueMin, 0) == 0);
  }

  return result;
}

// Forced instantiation for string
template class GateAttributeComparisonFilter<std::string>;
