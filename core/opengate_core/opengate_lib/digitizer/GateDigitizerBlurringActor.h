/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerGaussianBlurringActor_h
#define GateDigitizerGaussianBlurringActor_h

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
 * Digitizer module for blurring an attribute (single value only, not a vector).
 * Usually for energy or time.
 */

class GateDigitizerBlurringActor : public GateVDigitizerWithOutputActor {

public:
  // constructor
  explicit GateDigitizerBlurringActor(py::dict &user_info);

  // destructor
  ~GateDigitizerBlurringActor() override;

  void InitializeUserInput(py::dict &user_info) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  std::string fBlurAttributeName;
  GateVDigiAttribute *fOutputBlurAttribute{};
  double fBlurSigma;
  std::string fBlurMethod;
  double fBlurReferenceValue;
  double fBlurResolution;
  double fBlurSlope;

  // This member store the function used to blur (Gaussian, InverseSquare etc)
  std::function<double(double)> fBlurValue;

  double GaussianBlur(double value);

  double InverseSquare(double value);

  double Linear(double value);

  // During computation (thread local)
  struct threadLocalT {
    double *fAttDValue{};
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerGaussianBlurringActor_h
