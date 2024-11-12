/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSimulationStatisticsActor_h
#define GateSimulationStatisticsActor_h

#include "GateHelpers.h"
#include "GateVActor.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateSimulationStatisticsActor : public GateVActor {

public:
  // explicit GateSimulationStatisticsActor(std::string type_name);
  explicit GateSimulationStatisticsActor(py::dict &user_info);

  ~GateSimulationStatisticsActor() override;

  void InitializeUserInput(py::dict &user_info) override;

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called when the simulation end (master thread only)
  void EndSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  // Called every time the simulation is about to end (all threads)
  void EndOfSimulationWorkerAction(const G4Run *lastRun) override;

  // Called every time a Track starts (all threads)
  void PreUserTrackingAction(const G4Track *track) override;

  // Called every time a batch of step must be processed
  void SteppingAction(G4Step *) override;

  py::dict GetCounts();

protected:
  // Local data for the threads (each one has a copy)
  struct threadLocal_t {
    int fRunCount;
    long int fEventCount;
    long int fTrackCount;
    long int fStepCount;
    std::map<std::string, long int> fTrackTypes;
  };
  G4Cache<threadLocal_t> threadLocalData;

  // fCounts will contain the final dictionary of all data,
  std::map<std::string, long int> fCounts;
  std::map<std::string, double> fCountsD;
  std::map<std::string, std::string> fCountsStr;

  bool fTrackTypesFlag;
  std::map<std::string, long int> fTrackTypes;
  double fDuration;
  double fInitDuration;
  std::chrono::system_clock::time_point fStartTime;
  std::chrono::system_clock::time_point fStartRunTime;
  std::chrono::system_clock::time_point fStopTime;
  bool fStartRunTimeIsSet;
};

#endif // GateSimulationStatisticsActor_h
