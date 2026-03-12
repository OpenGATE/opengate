/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAttributeComparisonFilter.h"
#include <sstream>

// Explicitly instantiate the numeric types
template class GateAttributeComparisonFilter<double>;
template class GateAttributeComparisonFilter<int>;
// template class GateAttributeComparisonFilter<G4ThreeVector>; NOT YET

// Specialization for String ("contains" logic)
template <>
void GateAttributeComparisonFilter<std::string>::InitializeUserInfo(
    py::dict &user_info) {
  GateVFilter::InitializeUserInfo(user_info);
  fAttributeName = DictGetStr(user_info, "attribute");
  fCompareValue = DictGetStr(user_info, "compare_value");
  fCompareOperation = DictGetStr(user_info, "compare_operation");

  auto *dgm = GateDigiAttributeManager::GetInstance();
  auto *att = dgm->GetDigiAttribute(fAttributeName);
  fAttribute = dynamic_cast<GateTDigiAttribute<std::string> *>(
      dgm->CopyDigiAttribute(att));
  if (!fAttribute) {
    std::ostringstream oss;
    oss << "Error: Attribute '" << fAttributeName << "' type mismatch in filter.";
    Fatal(oss.str());
  }
  fAttribute->SetSingleValueMode(true);
}

// Specialised implementation for std::string (Equality instead of Range)
template <>
bool GateAttributeComparisonFilter<std::string>::Accept(G4Step *step) const {
  fAttribute->ProcessHits(step);
  const auto val = fAttribute->GetSingleValue();

  if (fCompareOperation == "eq") {
    return val == fCompareValue;
  }
  if (fCompareOperation == "ne") {
    return val != fCompareValue;
  }
  if (fCompareOperation == "contains") {
    return val.find(fCompareValue) != std::string::npos;
  }
  if (fCompareOperation == "not_contains") {
    return val.find(fCompareValue) == std::string::npos;
  }
  if (fCompareOperation == "start") {
    return val.rfind(fCompareValue, 0) == 0;
  }
  if (fCompareOperation == "not_start") {
    return val.rfind(fCompareValue, 0) != 0;
  }

  std::ostringstream oss;
  oss << "Unknown compare_operation '" << fCompareOperation
      << "' for attribute filter '" << fAttributeName << "'.";
  Fatal(oss.str());
  return false;
}

// Forced instantiation for string
template class GateAttributeComparisonFilter<std::string>;
