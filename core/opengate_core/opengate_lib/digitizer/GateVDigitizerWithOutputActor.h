/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVDigitizerWithOutputActor_h
#define GateVDigitizerWithOutputActor_h

#include "../GateVActor.h"
#include "G4Cache.hh"
#include "GateDigiCollection.h"
#include "GateDigiCollectionIterator.h"
#include "GateHelpersDigitizer.h"
#include "GateTDigiAttribute.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Base class for simple digitizer module with one input and one output
 * DigitCollections
 */

class GateVDigitizerWithOutputActor : public GateVActor {

public:
  explicit GateVDigitizerWithOutputActor(py::dict &user_info, bool MT_ready);

  ~GateVDigitizerWithOutputActor() override;

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called when the simulation end (master thread only)
  void EndSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event starts
  void BeginOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  void EndOfSimulationWorkerAction(const G4Run * /*unused*/) override;

protected:
  std::string fOutputFilename;
  std::string fInputDigiCollectionName;
  std::string fOutputDigiCollectionName;
  GateDigiCollection *fOutputDigiCollection;
  GateDigiCollection *fInputDigiCollection;
  std::vector<std::string> fUserSkipDigiAttributeNames;
  int fClearEveryNEvents;

  bool fInitializeRootTupleForMasterFlag;

  virtual void DigitInitializeNoParam();
  virtual void
  DigitInitialize(const std::vector<std::string> &attributes_not_in_filler);

  // During computation (thread local)
  struct threadLocalVDigitizerT {
    GateDigiAttributesFiller *fDigiAttributeFiller{};
    GateDigiCollection::Iterator fInputIter;
  };
  G4Cache<threadLocalVDigitizerT> fThreadLocalVDigitizerData;
};

#endif // GateVDigitizerWithOutputActor_h
