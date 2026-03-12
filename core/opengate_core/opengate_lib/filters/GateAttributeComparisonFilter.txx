/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "../digitizer/GateDigiCollectionManager.h"
#include "../digitizer/GateTDigiAttribute.h"
#include "../GateHelpersDict.h"
#include "../digitizer/GateDigiAttributeManager.h"
#include <pybind11/stl.h>
#include <sstream>

template <typename T>
GateAttributeComparisonFilter<T>::GateAttributeComparisonFilter() : GateVFilter() {
  }

template <typename T>
   void GateAttributeComparisonFilter<T>::InitializeUserInfo(py::dict &user_info) {
      GateVFilter::InitializeUserInfo(user_info);
      fAttributeName = DictGetStr(user_info, "attribute");
      fCompareValue = user_info["compare_value"].cast<T>();
      fCompareOperation = DictGetStr(user_info, "compare_operation");

      // We create a copy for thread safety during the simulation
      auto *dgm = GateDigiAttributeManager::GetInstance();
      auto *att = dgm->GetDigiAttribute(fAttributeName);
      auto *vatt = dgm->CopyDigiAttribute(att);
      fAttribute = dynamic_cast<GateTDigiAttribute<T> *>(vatt);
      fAttribute->SetSingleValueMode(true);

      // Basic safety check for the cast
      if (!fAttribute) {
         std::ostringstream oss;
         oss << "Error: Attribute '" << fAttributeName << "' type mismatch in filter.";
         Fatal(oss.str());
      }
   }

template <typename T>
   bool GateAttributeComparisonFilter<T>::Accept(G4Step *step) const {
      fAttribute->ProcessHits(step);
      // Get the first single value
      const auto value = fAttribute->GetSingleValue();

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
