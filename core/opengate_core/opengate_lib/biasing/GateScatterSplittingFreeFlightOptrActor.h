/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateOptrSplitComptonScatteringActor_h
#define GateOptrSplitComptonScatteringActor_h

#include "G4VBiasingOperator.hh"
#include "GateGammaFreeFlightOptn.h"
#include "GateScatterSplittingFreeFlightOptn.h"
#include "GateVBiasOptrActor.h"

namespace py = pybind11;

class GateScatterSplittingFreeFlightOptrActor : public GateVBiasOptrActor {

public:
  explicit GateScatterSplittingFreeFlightOptrActor(py::dict &user_info);
  ~GateScatterSplittingFreeFlightOptrActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void BeginOfRunAction(const G4Run *run) override;
  void BeginOfEventAction(const G4Event *) override;

  void StartTracking(const G4Track *) override;
  void SteppingAction(G4Step *) override;
  void EndOfSimulationWorkerAction(const G4Run *) override;

  std::map<std::string, double> GetBiasInformation();

  void SetInvolvedBiasActor(GateVBiasOptrActor *actor) { fActor = actor; }

  static int IsScatterInteractionGeneralProcess_OLD(
      const G4BiasingProcessInterface *callingProcess);

  static int
  IsScatterInteraction(const G4BiasingProcessInterface *callingProcess);

  static bool IsFreeFlight(const G4Track *track);
  static constexpr int fThisIsAFreeFlightTrack = 666;

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
    GateGammaFreeFlightOptn *fFreeFlightOperation = nullptr;
    GateScatterSplittingFreeFlightOptn *fComptonSplittingOperation = nullptr;
    GateScatterSplittingFreeFlightOptn *fRayleighSplittingOperation = nullptr;
    int fComptonInteractionCount;
    std::map<std::string, double> fBiasInformationPerThread;
    bool fCurrentTrackIsFreeFlight;
    bool fIsTrackValidForStep;
  };
  G4Cache<threadLocal_t> threadLocalData;

  std::vector<std::string> fKillVolumes;
  std::vector<const G4LogicalVolume *> fKillLogicalVolumes;
  std::map<std::string, double> fBiasInformation;
  int fComptonSplittingFactor;
  int fRayleighSplittingFactor;
  int fMaxComptonLevel;
  GateVBiasOptrActor *fActor = nullptr;
};

#endif
