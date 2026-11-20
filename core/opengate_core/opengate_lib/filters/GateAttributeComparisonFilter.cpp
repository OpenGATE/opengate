/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAttributeComparisonFilter.h"
#include "../GateHelpersDict.h"
#include "../digitizer/GateDigiAttributeManager.h"
#include <sstream>

// Explicitly instantiate the numeric types
template class GateAttributeComparisonFilter<double>;
template class GateAttributeComparisonFilter<int>;

// Specialization for String ("contains" logic)
template <>
void GateAttributeComparisonFilter<std::string>::InitializeUserInfo(
    py::dict &user_info) {
  GateVFilter::InitializeUserInfo(user_info);
  fAttributeName = DictGetStr(user_info, "attribute");
  fCompareValue = DictGetStr(user_info, "compare_value");
  fCompareOperation = DictGetStr(user_info, "compare_operation");

  fAuxiliaryAttribute =
      GateVAuxiliaryAttribute::GetAuxiliaryAttributeByName(fAttributeName);
  if (fAuxiliaryAttribute != nullptr) {
    if (fAuxiliaryAttribute->GetDigiAttributeType() != 'S') {
      std::ostringstream oss;
      oss << "Error: Auxiliary attribute '" << fAttributeName
          << "' type mismatch in filter.";
      Fatal(oss.str());
    }
    return;
  }

  auto *dgm = GateDigiAttributeManager::GetInstance();
  auto *att = dgm->GetDigiAttribute(fAttributeName);
  fAttribute = dynamic_cast<GateTDigiAttribute<std::string> *>(
      dgm->CopyDigiAttribute(att));
  if (!fAttribute) {
    std::ostringstream oss;
    oss << "Error: Attribute '" << fAttributeName
        << "' type mismatch in filter.";
    Fatal(oss.str());
  }
  fAttribute->SetSingleValueMode(true);
}

// Specialised implementation for std::string (Equality instead of Range)
template <>
bool GateAttributeComparisonFilter<std::string>::Evaluate(G4Step *step) const {
  std::string val;
  if (fAuxiliaryAttribute != nullptr) {
    val = fAuxiliaryAttribute->GetSValue(step);
  } else {
    fAttribute->ProcessHits(step);
    val = fAttribute->GetSingleValue();
  }

  if (fCompareOperation == "eq") {
    return val == fCompareValue;
  }
  if (fCompareOperation == "ne") {
    return val != fCompareValue;
  }
  if (fCompareOperation == "contains") {
    return val.find(fCompareValue) != std::string::npos;
  }
  if (fCompareOperation == "startswith") {
    return val.rfind(fCompareValue, 0) == 0;
  }

  std::ostringstream oss;
  oss << "Unknown compare_operation '" << fCompareOperation
      << "' for attribute filter '" << fAttributeName << "'.";
  Fatal(oss.str());
  return false;
}

// Forced instantiation for string
template class GateAttributeComparisonFilter<std::string>;

// --------------------------------------------------------------------
// One component of a 3-vector attribute
GateAttributeFilterVectorComponent::GateAttributeFilterVectorComponent()
    : GateVFilter() {}

void GateAttributeFilterVectorComponent::InitializeUserInfo(
    py::dict &user_info) {
  GateVFilter::InitializeUserInfo(user_info);
  fAttributeName = DictGetStr(user_info, "vector_attribute");
  fComponent = DictGetInt(user_info, "component");
  fCompareValue = DictGetDouble(user_info, "compare_value");
  fCompareOperation = DictGetStr(user_info, "compare_operation");
  if (fComponent < 0 || fComponent > 2) {
    std::ostringstream oss;
    oss << "Error: the component of the attribute '" << fAttributeName
        << "' must be 0, 1 or 2 (X, Y or Z), while it is " << fComponent;
    Fatal(oss.str());
  }

  fAuxiliaryAttribute =
      GateVAuxiliaryAttribute::GetAuxiliaryAttributeByName(fAttributeName);
  if (fAuxiliaryAttribute != nullptr) {
    if (fAuxiliaryAttribute->GetDigiAttributeType() != '3') {
      std::ostringstream oss;
      oss << "Error: Auxiliary attribute '" << fAttributeName
          << "' is not a 3-vector, it cannot be used with _X, _Y or _Z.";
      Fatal(oss.str());
    }
    return;
  }

  // We create a copy for thread safety during the simulation
  auto *dgm = GateDigiAttributeManager::GetInstance();
  auto *att = dgm->GetDigiAttribute(fAttributeName);
  fAttribute = dynamic_cast<GateTDigiAttribute<G4ThreeVector> *>(
      dgm->CopyDigiAttribute(att));
  if (!fAttribute) {
    std::ostringstream oss;
    oss << "Error: Attribute '" << fAttributeName
        << "' is not a 3-vector, it cannot be used with _X, _Y or _Z.";
    Fatal(oss.str());
  }
  fAttribute->SetSingleValueMode(true);
}

bool GateAttributeFilterVectorComponent::Evaluate(G4Step *step) const {
  G4ThreeVector v;
  if (fAuxiliaryAttribute != nullptr) {
    v = fAuxiliaryAttribute->Get3Value(step);
  } else {
    fAttribute->ProcessHits(step);
    v = fAttribute->GetSingleValue();
  }
  const double value = v[fComponent];

  if (fCompareOperation == "lt") {
    return value < fCompareValue;
  }
  if (fCompareOperation == "le") {
    return value <= fCompareValue;
  }
  if (fCompareOperation == "gt") {
    return value > fCompareValue;
  }
  if (fCompareOperation == "ge") {
    return value >= fCompareValue;
  }
  if (fCompareOperation == "eq") {
    return value == fCompareValue;
  }
  if (fCompareOperation == "ne") {
    return value != fCompareValue;
  }

  std::ostringstream oss;
  oss << "Unknown compare_operation '" << fCompareOperation
      << "' for attribute filter '" << fAttributeName << "'.";
  Fatal(oss.str());
  return false;
}
