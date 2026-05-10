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
  GateVFilter::InitializeUserInfo(user_info);
  std::string op = DictGetStr(user_info, "operator");
  if (op == "and")
    fOperator = LogicOp::AND;
  else if (op == "or")
    fOperator = LogicOp::OR;

  // In the Python side, we will pass the list of actual C++ filter objects
  if (user_info.contains("filters")) {
    fFilters = user_info["filters"].cast<std::vector<GateVFilter *>>();
  }
}

bool GateBooleanFilter::Evaluate(G4Step *step) const {
  if (fFilters.empty())
    return true;

  if (fOperator == LogicOp::AND) {
    for (auto *f : fFilters)
      if (!f->Accept(step))
        return false;
    return true;
  } else {
    for (auto *f : fFilters)
      if (f->Accept(step))
        return true;
    return false;
  }
}

bool GateBooleanFilter::Evaluate(const G4Track *track) const {
  if (fFilters.empty())
    return true;

  if (fOperator == LogicOp::AND) {
    for (auto *f : fFilters)
      if (!f->Accept(track))
        return false;
    return true;
  } else {
    for (auto *f : fFilters)
      if (f->Accept(track))
        return true;
    return false;
  }
}
