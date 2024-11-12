/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerEfficiencyActor_h
#define GateDigitizerEfficiencyActor_h

#include "../GateVActor.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionIterator.h"
#include "GateHelpersDigitizer.h"
#include "GateTDigiAttribute.h"
#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Digitizer module for simulating detector efficiency.
 */

class GateDigitizerEfficiencyActor : public GateVDigitizerWithOutputActor {

public:
  // constructor
  explicit GateDigitizerEfficiencyActor(py::dict &user_info);

  void InitializeUserInput(py::dict &user_info) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  std::string fEfficiencyAttributeName;
  GateVDigiAttribute *fOutputEfficiencyAttribute{};
  double fEfficiency;

  // During computation (thread local)
  struct threadLocalT {
    double *fAttDValue{};
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerEfficiencyActor_h
