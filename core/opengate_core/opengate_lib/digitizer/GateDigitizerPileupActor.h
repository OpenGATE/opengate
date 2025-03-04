/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerPileupActor_h
#define GateDigitizerPileupActor_h

#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <G4Navigator.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Digitizer module for pile-up.
 */

class GateDigitizerPileupActor : public GateVDigitizerWithOutputActor {

public:
  // Constructor
  explicit GateDigitizerPileupActor(py::dict &user_info);

  // Destructor
  ~GateDigitizerPileupActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  // During computation (thread local)
  struct threadLocalT {};
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GateDigitizerPileupActor_h
