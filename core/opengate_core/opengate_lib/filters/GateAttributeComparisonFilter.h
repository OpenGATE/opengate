/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAttributeComparisonFilter_h
#define GateAttributeComparisonFilter_h

#include "../GateVAuxiliaryAttribute.h"
#include "../digitizer/GateTDigiAttribute.h"
#include "GateVFilter.h"

/*
 * Generic comparison filter for named runtime attributes.
 *
 * Resolution order is:
 * 1. auxiliary-attribute registry
 * 2. conventional DigiAttribute registry as fallback
 *
 * This lets the same user-facing filter syntax work for both simulation-level
 * auxiliary attributes and the older DigiAttribute-based values.
 */
template <typename T> class GateAttributeComparisonFilter : public GateVFilter {
public:
  GateAttributeComparisonFilter();

  void InitializeUserInfo(py::dict &user_info) override;

  bool Evaluate(G4Step *step) const override;

  std::string fAttributeName;
  T fCompareValue;
  std::string fCompareOperation;
  GateTDigiAttribute<T> *fAttribute{nullptr};
  GateVAuxiliaryAttribute *fAuxiliaryAttribute{nullptr};
};

// Typedefs for common use cases
using GateAttributeFilterDouble = GateAttributeComparisonFilter<double>;
using GateAttributeFilterInt = GateAttributeComparisonFilter<int>;
using GateAttributeFilterString = GateAttributeComparisonFilter<std::string>;

// --------------------------------------------------------------------
// NEW: Explicit Specialization Declarations
// This tells the compiler NOT to instantiate the generic .txx version
// for std::string, preventing the LNK2005 error on Windows.
template <>
void GateAttributeComparisonFilter<std::string>::InitializeUserInfo(
    py::dict &user_info);

template <>
bool GateAttributeComparisonFilter<std::string>::Evaluate(G4Step *step) const;
// --------------------------------------------------------------------

/*
 * Comparison of one component (x, y or z) of a 3-vector attribute (e.g.
 * PostPosition, PreDirection) with a double value. The component index is 0, 1
 * or 2. Used in Python with F.PostPosition_X < 0 (same for _Y, _Z).
 */
class GateAttributeFilterVectorComponent : public GateVFilter {
public:
  GateAttributeFilterVectorComponent();

  void InitializeUserInfo(py::dict &user_info) override;

  bool Evaluate(G4Step *step) const override;

  std::string fAttributeName;
  int fComponent{0};
  double fCompareValue{0};
  std::string fCompareOperation;
  GateTDigiAttribute<G4ThreeVector> *fAttribute{nullptr};
  GateVAuxiliaryAttribute *fAuxiliaryAttribute{nullptr};
};

#include "GateAttributeComparisonFilter.txx"

#endif // GateAttributeComparisonFilter_h
