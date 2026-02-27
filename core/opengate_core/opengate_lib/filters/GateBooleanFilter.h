/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateBooleanFilter_h
#define GateBooleanFilter_h

#include "GateVFilter.h"
#include <vector>

class GateBooleanFilter : public GateVFilter {
public:
  enum class LogicOp { AND, OR, NOT };

  GateBooleanFilter();
  virtual ~GateBooleanFilter();

  void InitializeUserInfo(py::dict &user_info) override;

  // The core recursive logic
  bool Accept(G4Step *step) const override;
  bool Accept(const G4Track *track) const override;

  void SetOperator(LogicOp op) { fOperator = op; }
  void AddFilter(GateVFilter *filter) { fFilters.push_back(filter); }

private:
  std::vector<GateVFilter *> fFilters;
  LogicOp fOperator = LogicOp::AND;
};

#endif