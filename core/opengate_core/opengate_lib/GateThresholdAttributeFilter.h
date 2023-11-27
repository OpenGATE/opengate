/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateThresholdAttributeFilter_h
#define GateThresholdAttributeFilter_h

#include "G4Step.hh"
#include "G4Track.hh"
#include "GateVFilter.h"
#include "digitizer/GateDigiCollectionManager.h"
#include "digitizer/GateTDigiAttribute.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateThresholdAttributeFilter : public GateVFilter {

public:
  GateThresholdAttributeFilter();

  void Initialize(py::dict &user_info) override;

  // To avoid gcc -Woverloaded-virtual
  // https://stackoverflow.com/questions/9995421/gcc-woverloaded-virtual-warnings
  using GateVFilter::Accept;

  bool Accept(const G4Track *track) const override;

  bool Accept(G4Step *step) const override;

  std::string fAttributeName;
  std::string fPolicy;
  double fValueMin{};
  double fValueMax{};
  bool fKeep{};
  std::string fFilterName;
  GateDigiCollection *fDigiCollection{};
  GateTDigiAttribute<double> *fAttribute{};
};

#endif // GateThresholdAttributeFilter_h
