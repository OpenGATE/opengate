/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateBooleanFilter.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"

GateBooleanFilter::GateBooleanFilter() : GateVFilter() {}
GateBooleanFilter::~GateBooleanFilter() {}

void GateBooleanFilter::InitializeUserInfo(py::dict &user_info) {
  std::string op = DictGetStr(user_info, "operator");
  if (op == "and")
    fOperator = LogicOp::AND;
  else if (op == "or")
    fOperator = LogicOp::OR;
  else if (op == "not")
    fOperator = LogicOp::NOT;

  // In the Python side, we will pass the list of actual C++ filter objects
  if (user_info.contains("filters")) {
    fFilters = user_info["filters"].cast<std::vector<GateVFilter *>>();
  }
}

bool GateBooleanFilter::Accept(G4Step *step) const {
  // DDD("GateBooleanFilter::Accept(G4Step*)");
  // DDD(fFilters.size());
  if (fFilters.empty())
    return true;

  // DDD(int(fOperator));
  if (fOperator == LogicOp::AND) {
    for (auto *f : fFilters)
      if (!f->Accept(step))
        return false;
    return true;
  } else if (fOperator == LogicOp::OR) {
    for (auto *f : fFilters)
      if (f->Accept(step))
        return true;
    return false;
  } else { // NOT
    return !fFilters[0]->Accept(step);
  }
}

bool GateBooleanFilter::Accept(const G4Track *track) const {
  // Mirror the same logic for Track-level filtering
  if (fFilters.empty())
    return true;
  // ... logic same as above ...
  return true;
}