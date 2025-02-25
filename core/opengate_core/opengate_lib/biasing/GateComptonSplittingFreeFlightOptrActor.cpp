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
  fMaxComptonLevel = 1;
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
  GateVActor::InitializeUserInfo(user_info);

  // Get user parameters
  fSplittingFactor = DictGetInt(user_info, "splitting_factor");
  fMaxComptonLevel = DictGetInt(user_info, "max_compton_level");

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

    // Check GeneralGammaProcess
    if (G4EmParameters::Instance()->GeneralProcessActive() == false) {
      Fatal("GeneralGammaProcess is not active. This is needed for "
            "ComptonSplittingFreeFlightActor");
    }
  }
}

void GateComptonSplittingFreeFlightOptrActor::BeginOfEventAction(
    const G4Event *event) {
  threadLocal_t &l = threadLocalData.Get();
  l.fSetOfTrackIDThatDidCompton.clear();
  l.fComptonInteractionCount = 0;
  l.fCurrentTrackIsFreeFlight = false;
  // DDD(event->GetEventID());
}

void GateComptonSplittingFreeFlightOptrActor::StartTracking(
    const G4Track *track) {
  // A new track is being tracked
  threadLocal_t &l = threadLocalData.Get();
  l.fComptonInteractionCount = 0;
  l.fCurrentTrackIsFreeFlight = false;
  l.fSplitStatsPerThread["nb_tracks"] += 1;
  // DDD("StartTracking");
  // DDD(track->GetTrackID());

  // It maybe either (1) conventional gamma that we track for Compton
  // or (2) a previous split Compton scatter that we track with free flight

  // If no creator process (this is a source event), this is case (1)
  const auto *creator_process = track->GetCreatorProcess();
  // const auto tid = track->GetTrackID();
  if (creator_process == nullptr)
    return;

  // Otherwise, we check if the parent id was a split Compton (in that volume)
  const auto pid = track->GetParentID();
  bool parent_is_compton = l.fSetOfTrackIDThatDidCompton.find(pid) !=
                           l.fSetOfTrackIDThatDidCompton.end();

  // DDD(parent_is_compton);
  // If this is not a previous split Compton, this is case (1), no free flight
  if (!parent_is_compton)
    return;

  // Checking if the process that "create" the gamma was Compton
  // const auto *bp =
  //    dynamic_cast<const G4BiasingProcessInterface *>(creator_process);
  //// DDD(IsComptonInteraction(bp));
  /*if (IsComptonInteraction(bp)) {*/
  // This track is free flight
  l.fCurrentTrackIsFreeFlight = true;
  // we need to start the ff with the correct weight
  // FIXME MUST BE 1 ???
  // DDD(track->GetWeight());
  /*if (track->GetWeight() != 1.0 / fSplittingFactor)
  {
      DDD(track->GetWeight());
      DDD(pid);
  }*/
  l.fFreeFlightOperation->ResetInitialTrackWeight(1.0 / fSplittingFactor);
  l.fSplitStatsPerThread["nb_tracks_with_free_flight"] += 1;
  //}
}

G4VBiasingOperation *
GateComptonSplittingFreeFlightOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
  // DDD("ProposeNonPhysicsBiasingOperation");
  return nullptr;
}

G4VBiasingOperation *
GateComptonSplittingFreeFlightOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // Should we track the particle with free flight or not ?
  const threadLocal_t &l = threadLocalData.Get();
  // DDD(l.fCurrentTrackIsFreeFlight);
  if (l.fCurrentTrackIsFreeFlight)
    return l.fFreeFlightOperation;

  // Conventional tracking
  return nullptr;
}

G4VBiasingOperation *
GateComptonSplittingFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // Go in this function every interaction (not Transportation)

  // Check if this is free flight
  threadLocal_t &l = threadLocalData.Get();
  if (l.fCurrentTrackIsFreeFlight)
    return callingProcess->GetCurrentOccurenceBiasingOperation();

  // Check if this is a Compton
  const auto tid = track->GetTrackID();
  // DDD(track->GetPosition());
  // DDD(IsComptonInteraction(callingProcess));
  if (IsComptonInteraction(callingProcess)) {
    // There is a new Compton, split it
    l.fComptonInteractionCount++;
    // DDD(l.fComptonInteractionCount);
    if (l.fComptonInteractionCount <= fMaxComptonLevel) {
      l.fSetOfTrackIDThatDidCompton.insert(tid); // FIXME check set unique ?
      l.fSplitStatsPerThread["nb_splits"] += 1;
      return l.fComptonSplittingOperation;
    }
  }

  // This is not a Compton
  return callingProcess->GetCurrentOccurenceBiasingOperation();
}

void GateComptonSplittingFreeFlightOptrActor::SteppingAction(G4Step *step) {
  // Go in this function every step, even Transportation

  threadLocal_t &l = threadLocalData.Get();
  if (l.fCurrentTrackIsFreeFlight) {
    // DDD(step->GetTrack()->GetWeight());
    return;
  }

  // DDD(DebugStep(step));

  // if not free flight, we kill the gamma if it exits the volume
  // Exiting the volume is tricky : need to check the post point
  // is in the mother volume.
  if (IsStepExitVolume(step)) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fSplitStatsPerThread["nb_killed_gammas_exiting"] += 1;
    return;
  }

  // if too much Compton, we kill the gamma
  if (l.fComptonInteractionCount > fMaxComptonLevel) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fSplitStatsPerThread["nb_killed_gammas_compton_level"] += 1;
    return;
  }

  // keep only gamma
  if (step->GetTrack()->GetDefinition()->GetParticleName() != "gamma") {
    // kill it without mercy
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fSplitStatsPerThread["nb_killed_non_gamma_particles"] += 1;
  }
}

void GateComptonSplittingFreeFlightOptrActor::EndOfSimulationWorkerAction(
    const G4Run *) {
  G4AutoLock mutex(&StatMutex);
  const threadLocal_t &l = threadLocalData.Get();
  for (const auto &m : l.fSplitStatsPerThread) {
    if (fSplitStats.count(m.first) == 0)
      fSplitStats[m.first] = 0;
    fSplitStats[m.first] += m.second;
  }
}

bool GateComptonSplittingFreeFlightOptrActor::IsComptonInteraction(
    const G4BiasingProcessInterface *callingProcess) const {
  // If GammaGeneralProc is used, we need to retrieve the real process within
  // GetSelectedProcess (with SelectedProcess)

  // If GammaGeneralProc is not used, the free flight is not
  // correct when it biases several processes (compt + Rayl + phot + conv).
  // Unsure why.

  // Retrieve the wrapped process
  const auto *wrapped_p = callingProcess->GetWrappedProcess();

  // We "know" this is a GammaGeneralProcess
  const auto *ggp = static_cast<const G4GammaGeneralProcess *>(wrapped_p);

  /*
  GetSubProcessName() = compt  GetSubProcessSubType() = 13
  GetSubProcessName() = Rayl   GetSubProcessSubType() = 11
  GetSubProcessName() = phot   GetSubProcessSubType() = 12

  Unsure what it is:
  GetSubProcessName() = GammaGeneralProc  GetSubProcessSubType() = 16
  */

  // || ggp->GetSubProcessSubType() == 16) ? unsure ? // FIXME ?????????
  if (ggp->GetSubProcessSubType() == 13 || ggp->GetSubProcessSubType() == 16)
    return true;
  return false;

  // DDD(ggp->GetProcessName());
  // ggp->ProcessDescription(std::cout);
  // DDD(ggp->GetSubProcessName());
  // DDD(ggp->GetSubProcessSubType());

  const auto *cp = ggp->GetCreatorProcess();
  if (cp != nullptr) {
    // DDD(cp->GetProcessName());
  }

  // We extract the real sub (selected) process
  const auto *proc = ggp->GetSelectedProcess();
  if (proc != nullptr) {
    // DDD(proc->GetProcessName());
  }
  if (proc != nullptr && proc->GetProcessName() == "compt")
    return true;
  return false;
}
