/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateOptrSplitComptonScatteringActor_h
#define GateOptrSplitComptonScatteringActor_h

#include "G4BOptnForceFreeFlight.hh"
#include "G4VBiasingOperator.hh"
#include "GateComptonSplittingFreeFlightOptn.h"
#include "GateVBiasOptrActor.h"

namespace py = pybind11;

class GateComptonSplittingFreeFlightOptrActor : public GateVBiasOptrActor {

public:
  explicit GateComptonSplittingFreeFlightOptrActor(py::dict &user_info);
  ~GateComptonSplittingFreeFlightOptrActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void BeginOfRunAction(const G4Run *run) override;
  void BeginOfEventAction(const G4Event *) override;
  void StartTracking(const G4Track *) override;
  void SteppingAction(G4Step *) override;
  void EndOfSimulationWorkerAction(const G4Run *) override;

  std::map<std::string, double> GetSplitStats();

protected:
  G4VBiasingOperation *
  ProposeNonPhysicsBiasingOperation(const G4Track *,
                                    const G4BiasingProcessInterface *) override;

  G4VBiasingOperation *
  ProposeOccurenceBiasingOperation(const G4Track *,
                                   const G4BiasingProcessInterface *) override;

  G4VBiasingOperation *ProposeFinalStateBiasingOperation(
      const G4Track *track,
      const G4BiasingProcessInterface *callingProcess) override;

  struct threadLocal_t {
    G4BOptnForceFreeFlight *fFreeFlightOperation = nullptr;
    GateComptonSplittingFreeFlightOptn *fComptonSplittingOperation = nullptr;
    std::set<int> fSetOfTrackIDForFreeFlight;
    std::set<int> fSetOfTrackIDThatDidCompton;
    int fComptonInteractionCount;
    std::map<std::string, double> fSplitStatsPerThread;
  };
  G4Cache<threadLocal_t> threadLocalData;

  std::map<std::string, double> fSplitStats;

  int fSplittingFactor;
  int fMaxComptonInteractionCount;
};

#endif
