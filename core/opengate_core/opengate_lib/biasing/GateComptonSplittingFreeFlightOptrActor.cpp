/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateComptonSplittingFreeFlightOptrActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "G4BiasingProcessInterface.hh"
#include "G4GammaGeneralProcess.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "GateComptonSplittingFreeFlightOptn.h"

G4Mutex StatMutex = G4MUTEX_INITIALIZER;

GateComptonSplittingFreeFlightOptrActor::
    GateComptonSplittingFreeFlightOptrActor(py::dict &user_info)
    : GateVBiasOptrActor("FreeFlightOperator", user_info, true) {
  fSplittingFactor = 1;
  fMaxComptonInteractionCount = 1;
  fSplitStats.clear();
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndOfSimulationWorkerAction");
}

GateComptonSplittingFreeFlightOptrActor::
    ~GateComptonSplittingFreeFlightOptrActor() {
  threadLocal_t &l = threadLocalData.Get();
  delete l.fFreeFlightOperation;
  delete l.fComptonSplittingOperation;
}

std::map<std::string, double>
GateComptonSplittingFreeFlightOptrActor::GetSplitStats() {
  return fSplitStats;
}

void GateComptonSplittingFreeFlightOptrActor::InitializeUserInfo(
    py::dict &user_info) {
  std::cout << "GateOptrSplitComptonScatteringActor InitializeUserInfo"
            << std::endl;
  GateVActor::InitializeUserInfo(user_info);
  fSplittingFactor = DictGetInt(user_info, "splitting_factor");
  fMaxComptonInteractionCount = DictGetInt(user_info, "max_compton_level");

  // Create the FF operation
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation = new G4BOptnForceFreeFlight("FreeFlightOperation");

  // Create the Compton splitting operation
  l.fComptonSplittingOperation =
      new GateComptonSplittingFreeFlightOptn("ComptonSplittingOperation");
  l.fComptonSplittingOperation->SetSplittingFactor(fSplittingFactor);

  // Initialize the AA (Angular Acceptance) for the Compton operation
  const auto dd = py::dict(user_info["acceptance_angle"]);
  l.fComptonSplittingOperation->InitializeAAManager(dd);
}

void GateComptonSplittingFreeFlightOptrActor::BeginOfRunAction(
    const G4Run *run) {
  if (run->GetRunID() == 0) {
    threadLocal_t &l = threadLocalData.Get();
    l.fSplitStatsPerThread["nb_tracks"] = 0;
    l.fSplitStatsPerThread["nb_tracks_with_free_flight"] = 0;
    l.fSplitStatsPerThread["nb_splits"] = 0;
    l.fSplitStatsPerThread["nb_killed_non_gamma_particles"] = 0;
    l.fSplitStatsPerThread["nb_killed_gammas_compton_level"] = 0;
    l.fSplitStatsPerThread["nb_killed_gammas_exiting"] = 0;
  }
}

void GateComptonSplittingFreeFlightOptrActor::BeginOfEventAction(
    const G4Event *event) {
  threadLocal_t &l = threadLocalData.Get();
  l.fSetOfTrackIDForFreeFlight.clear();
  l.fSetOfTrackIDThatDidCompton.clear();
  l.fComptonInteractionCount = 0;
}

void GateComptonSplittingFreeFlightOptrActor::StartTracking(
    const G4Track *track) {
  // A new track is being tracked
  threadLocal_t &l = threadLocalData.Get();
  l.fComptonInteractionCount = 0;
  l.fSplitStatsPerThread["nb_tracks"] += 1;

  // DDD(track->GetTrackID());
  const auto *creator_process = track->GetCreatorProcess();
  const auto tid = track->GetTrackID();
  if (creator_process != nullptr) {
    // if the parent id was a split Compton (in that volume)
    // Unsure if needed (maybe Compton can be done outside the volume)
    const auto pid = track->GetParentID();
    bool is_free_flight = l.fSetOfTrackIDThatDidCompton.count(pid) == 1;
    if (is_free_flight) {
      // DDD(creator_process->GetProcessName());
      const auto *bp =
          static_cast<const G4BiasingProcessInterface *>(creator_process);
      // DDD(bp);
      // if (bp != nullptr) {
      const auto *wrapped_p = bp->GetWrappedProcess();
      const auto *ggp = static_cast<const G4GammaGeneralProcess *>(wrapped_p);
      const auto *proc = ggp->GetSelectedProcess();
      if (proc != nullptr) {
        // DDD(proc->GetProcessName());
        //  and if the process is a Compton
        if (proc->GetProcessName() == "compt") {
          // We add this id to track it with free flight
          l.fSetOfTrackIDForFreeFlight.insert(tid);
          // we need to start the ff with the correct weight
          // l.fFreeFlightOperation->ResetInitialTrackWeight(track->GetWeight());
          // l.fFreeFlightOperation->ResetInitialTrackWeight(1.0);
          l.fFreeFlightOperation->ResetInitialTrackWeight(1.0 /
                                                          fSplittingFactor);
          l.fSplitStatsPerThread["nb_tracks_with_free_flight"] += 1;
          // DDD(track->GetWeight());
          // DDD(track->GetDynamicParticle()->GetKineticEnergy());
        }
        //}
      }
    }
  }
}

G4VBiasingOperation *
GateComptonSplittingFreeFlightOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
  return nullptr;
}

G4VBiasingOperation *
GateComptonSplittingFreeFlightOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // Should we track the particle with free flight or not ?
  const threadLocal_t &l = threadLocalData.Get();
  const auto tid = track->GetTrackID();
  bool is_free_flight = l.fSetOfTrackIDForFreeFlight.count(tid) > 0;
  if (is_free_flight) {
    // free flight tracking
    // DDD(track->GetWeight());
    // DDD(track->GetDynamicParticle()->GetKineticEnergy());
    return l.fFreeFlightOperation;
  }
  // normal tracking
  return nullptr;
}

G4VBiasingOperation *
GateComptonSplittingFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {

  // Check if this is free flight
  threadLocal_t &l = threadLocalData.Get();

  /*for (auto s: l.fSetOfTrackIDForFreeFlight) {
      DDD(s);
  }*/

  const auto tid = track->GetTrackID();
  bool is_free_flight = l.fSetOfTrackIDForFreeFlight.count(tid) > 0;
  // DDD(is_free_flight);
  if (is_free_flight) {
    // DDD("free flight");
    // exit(0);
    return callingProcess->GetCurrentOccurenceBiasingOperation();
  }

  /*DDD(callingProcess->GetProcessName());
  DDD(callingProcess->GetProcessSubType());
  DDD(callingProcess->GetWrappedProcess()->GetProcessName());
  G4GammaGeneralProcess *p = (G4GammaGeneralProcess *)
  callingProcess->GetWrappedProcess(); DDD(p->GetSubProcessName());
  DDD(p->GetProcessName());
  if (p->GetSelectedProcess() != nullptr) {
      DDD(p->GetSelectedProcess()->GetProcessName());
  }*/

  // Check if this is a Compton
  // If GammaGeneralProc is used, we need to retrieve the real process with
  // GetSelectedProcess If GammaGeneralProc is not used, the free flight is not
  // correct when it biases several processes (compt + Rayl + phot + conv).
  // Unsure why.
  const auto *wrapped_p = callingProcess->GetWrappedProcess();
  const auto &proc_name = wrapped_p->GetProcessName();
  if (proc_name != "GammaGeneralProc") {
    std::ostringstream oss;
    oss << "GammaGeneralProc must be used" << std::endl;
    Fatal(oss.str()); // should never be here, this is checked on python side
  }
  const auto *ggp = (const G4GammaGeneralProcess *)wrapped_p;
  const auto *proc = ggp->GetSelectedProcess();
  // if (is_free_flight == false && callingProcess->GetProcessName() ==
  // "biasWrapper(compt)") { if (is_free_flight == false &&
  // proc->GetProcessName() == "compt") { DDD(is_free_flight); DDD(proc); if
  // (proc != nullptr) DDD(proc->GetProcessName());

  if (proc != nullptr && proc->GetProcessName() == "compt") {
    // There is a new Compton, split it
    l.fSetOfTrackIDThatDidCompton.insert(tid);
    l.fComptonInteractionCount++;
    // DDD(l.fComptonInteractionCount);
    if (l.fComptonInteractionCount <= fMaxComptonInteractionCount) {
      l.fSplitStatsPerThread["nb_splits"] += 1;
      return l.fComptonSplittingOperation;
    }
  }

  // This is not a Compton
  return callingProcess->GetCurrentOccurenceBiasingOperation();
}

void GateComptonSplittingFreeFlightOptrActor::SteppingAction(G4Step *step) {
  threadLocal_t &l = threadLocalData.Get();
  // keep only gamma
  if (step->GetTrack()->GetDefinition()->GetParticleName() != "gamma") {
    // kill it without mercy
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fSplitStatsPerThread["nb_killed_non_gamma_particles"] += 1;
    return;
  }

  // if too much Compton, we kill the gamma
  if (l.fComptonInteractionCount > fMaxComptonInteractionCount) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fSplitStatsPerThread["nb_killed_gammas_compton_level"] += 1;
    return;
  }

  // is free flight ?
  const auto tid = step->GetTrack()->GetTrackID();
  bool is_free_flight = l.fSetOfTrackIDForFreeFlight.count(tid) > 0;
  if (is_free_flight) {
    // DDD("ff");
    return;
  }

  // if not free flight, we kill the gamma if it exits the volume
  // Exiting the volume is tricky : need to check the post point
  // is in the mother volume.
  if (IsStepExitVolume(step)) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fSplitStatsPerThread["nb_killed_gammas_exiting"] += 1;
  }
}

void GateComptonSplittingFreeFlightOptrActor::EndOfSimulationWorkerAction(
    const G4Run *) {
  DDD("EndOfSimulationWorkerAction");
  G4AutoLock mutex(&StatMutex);
  const threadLocal_t &l = threadLocalData.Get();
  for (const auto &m : l.fSplitStatsPerThread) {
    if (fSplitStats.count(m.first) == 0)
      fSplitStats[m.first] = 0;
    fSplitStats[m.first] += m.second;
  }
}
