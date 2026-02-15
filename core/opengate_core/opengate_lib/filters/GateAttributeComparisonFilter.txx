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
#include <limits>
#include <pybind11/stl.h>

template <typename T>
GateAttributeComparisonFilter<T>::GateAttributeComparisonFilter() : GateVFilter() {
  }

template <typename T>
   void GateAttributeComparisonFilter<T>::InitializeUserInfo(py::dict &user_info) {
      GateVFilter::InitializeUserInfo(user_info);
      fAttributeName = DictGetStr(user_info, "attribute");

     // Check for value_min: must exist AND not be None
       if (user_info.contains("value_min") && !user_info["value_min"].is_none()) {
         fValueMin = user_info["value_min"].cast<T>();
       } else {
         fValueMin = std::numeric_limits<T>::lowest();
       }

       // Check for value_max: must exist AND not be None
       if (user_info.contains("value_max") && !user_info["value_max"].is_none()) {
         fValueMax = user_info["value_max"].cast<T>();
       } else {
         fValueMax = std::numeric_limits<T>::max();
       }

      // New: Handle strict vs non-strict flags
      fIncludeMin = user_info["include_min"].cast<bool>();
      fIncludeMax = user_info["include_max"].cast<bool>();

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
      // Get the first value (e.g., KineticEnergy at the start of step)
      const auto value = fAttribute->GetSingleValue();
      bool result = true;

     if (fIncludeMin) { if (value < fValueMin) result = false; }
     else { if (value <= fValueMin) result = false; }

     if (fIncludeMax) { if (value > fValueMax) result = false; }
     else { if (value >= fValueMax) result = false; }

      //fAttribute->Clear();
      return result;
   }
