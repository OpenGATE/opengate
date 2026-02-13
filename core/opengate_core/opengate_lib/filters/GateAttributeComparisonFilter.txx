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
   void GateAttributeComparisonFilter<T>::InitializeUserInfo(py::dict &user_info) {
      GateVFilter::InitializeUserInfo(user_info);
      DDD("GateAttributeComparisonFilter InitializeUserInfo");
      fAttributeName = DictGetStr(user_info, "attribute");

      // Default to the full range of the data type if not provided
      fValueMin = user_info.contains("value_min") ? user_info["value_min"].cast<T>() : std::numeric_limits<T>::lowest();
      fValueMax = user_info.contains("value_max") ? user_info["value_max"].cast<T>() : std::numeric_limits<T>::max();

      DDD("init GateAttributeComparisonFilter");
      DDD(fName);
      DDD(fAttributeName);
      DDD(fValueMin);
      DDD(fValueMax);

      auto *dgm = GateDigiAttributeManager::GetInstance();
      auto *att = dgm->GetDigiAttribute(fAttributeName);

      // We create a copy for thread safety during the simulation
      auto *vatt = dgm->CopyDigiAttribute(att);
      fAttribute = dynamic_cast<GateTDigiAttribute<T> *>(vatt);

      // Basic safety check for the cast
      if (!fAttribute) {
         std::ostringstream oss;
         oss << "Error: Attribute '" << fAttributeName << "' type mismatch in filter.";
         Fatal(oss.str());
      }
   }

template <typename T>
bool GateAttributeComparisonFilter<T>::Accept(const G4Track *track) const {
 DDD("track");
  return true;
}

template <typename T>
   bool GateAttributeComparisonFilter<T>::Accept(G4Step *step) const {
      //DDD("accept");
      fAttribute->ProcessHits(step);
      //DDD("here");
      // Get the first value (e.g., KineticEnergy at the start of step)
      const auto &values = fAttribute->GetValues();
      //DDV(values);
      bool result = true;

      if (!values.empty()) {
         T value = values[0];
         //DDD(T);
         // result = (value >= fValueMin && value <= fValueMax);
         // result = true;
         if (fIncludeMin) { if (value < fValueMin) result = false; }
         else { if (value <= fValueMin) result = false; }

         if (fIncludeMax) { if (value > fValueMax) result = false; }
         else { if (value >= fValueMax) result = false; }
      }
      //DDD(result);

      fAttribute->Clear();
      //DDD("after clear");
      return result;
   }
