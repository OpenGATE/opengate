/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGateDigitizerEnergyWindowsActor_H
#define OPENGATE_CORE_OPENGateDigitizerEnergyWindowsActor_H

#include "../GateVActor.h"
#include "G4Cache.hh"
#include "GateDigiCollection.h"
#include "GateHelpersDigitizer.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 * Simple actor that use a input Hits Collection and split into several ones
 * with some thresholds on the TotalEnergyDeposit
 */

class GateDigitizerEnergyWindowsActor : public GateVActor {

public:
  explicit GateDigitizerEnergyWindowsActor(py::dict &user_info);

  void InitializeUserInput(py::dict &user_info) override;

  void InitializeCpp() override;

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event starts
  void BeginOfEventAction(const G4Event *event) override;

  // Called every time a Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  // Called when the simulation end (all threads)
  void EndOfSimulationWorkerAction(const G4Run * /*run*/) override;

  // Called when the simulation end (master thread only)
  void EndSimulationAction() override;

  // Get the id of the last energy window
  int GetLastEnergyWindowId();

protected:
  std::string fInputDigiCollectionName;
  GateDigiCollection *fInputDigiCollection;
  std::vector<std::string> fUserSkipDigiAttributeNames;
  std::vector<GateDigiCollection *> fChannelDigiCollections;
  std::vector<std::string> fChannelNames;
  std::vector<double> fChannelMin;
  std::vector<double> fChannelMax;
  int fClearEveryNEvents;

  void ApplyThreshold(size_t i, double min, double max);

  // During computation
  struct threadLocalT {
    std::vector<GateDigiAttributesFiller *> fFillers;
    std::vector<double> *fInputEdep;
    int fLastEnergyWindowId;
  };
  G4Cache<threadLocalT> fThreadLocalData;
};

#endif // OPENGATE_CORE_OPENGateDigitizerEnergyWindowsActor_H
