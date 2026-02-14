/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAttributeComparisonFilter_h
#define GateAttributeComparisonFilter_h

#include "../GateHelpersDict.h"
#include "../digitizer/GateTDigiAttribute.h"
#include "G4Step.hh"
#include "GateVFilter.h"

template <typename T> class GateAttributeComparisonFilter : public GateVFilter {
public:
  GateAttributeComparisonFilter();

  void InitializeUserInfo(py::dict &user_info) override;

  // Implementation of Accept for Step
  bool Accept(G4Step *step) const override;

  std::string fAttributeName;
  T fValueMin;
  T fValueMax;
  bool fIncludeMin = true;
  bool fIncludeMax = true;
  std::string fSearchMode{"equal"};
  GateTDigiAttribute<T> *fAttribute{nullptr};
};

// Typedefs for common use cases
using GateAttributeFilterDouble = GateAttributeComparisonFilter<double>;
using GateAttributeFilterInt = GateAttributeComparisonFilter<int>;

#include "GateAttributeComparisonFilter.txx"

#endif // GateAttributeComparisonFilter_h
