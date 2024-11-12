/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePrimaryScatterFilter_h
#define GatePrimaryScatterFilter_h

#include "GateVFilter.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateUnscatteredPrimaryFilter : public GateVFilter {

public:
  GateUnscatteredPrimaryFilter() : GateVFilter() {}

  void InitializeUserInput(py::dict &user_info) override;

  // To avoid gcc -Woverloaded-virtual
  // https://stackoverflow.com/questions/9995421/gcc-woverloaded-virtual-warnings
  using GateVFilter::Accept;

  bool Accept(G4Step *step) const override;

  std::string fPolicy;
};

int IsUnscatteredPrimary(const G4Step *step);

#endif // GatePrimaryScatterFilter_h
