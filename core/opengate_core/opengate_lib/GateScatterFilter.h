/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateScatterFilter_h
#define GateScatterFilter_h

#include "GateVFilter.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateScatterFilter : public GateVFilter {

public:
  GateScatterFilter() : GateVFilter() {}

  void Initialize(py::dict &user_info) override;

  // To avoid gcc -Woverloaded-virtual
  // https://stackoverflow.com/questions/9995421/gcc-woverloaded-virtual-warnings
  using GateVFilter::Accept;

  bool Accept(G4Step *step) const override;

  std::string fPolicy;
};

int StepHasScatter(const G4Step *step);

#endif // GateScatterFilter_h
