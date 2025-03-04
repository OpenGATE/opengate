/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateScatterSplittingFreeFlightOptrActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "GateScatterSplittingFreeFlightOptn.h"

#include "G4BiasingProcessInterface.hh"
#include "G4GammaGeneralProcess.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"

G4Mutex StatMutex = G4MUTEX_INITIALIZER;

GateScatterSplittingFreeFlightOptrActor::
    GateScatterSplittingFreeFlightOptrActor(py::dict &user_info)
    : GateVBiasOptrActor("FreeFlightOperator", user_info, true) {
  fComptonSplittingFactor = 1;
  fRayleighSplittingFactor = 1;
  fMaxComptonLevel = 1;
  fSplitStats.clear();
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndOfSimulationWorkerAction");
}

GateScatterSplittingFreeFlightOptrActor::
    ~GateScatterSplittingFreeFlightOptrActor() {
  threadLocal_t &l = threadLocalData.Get();
  delete l.fFreeFlightOperation;
  delete l.fRayleighSplittingOperation;
  delete l.fComptonSplittingOperation;
}

std::map<std::string, double>
GateScatterSplittingFreeFlightOptrActor::GetSplitStats() {
  return fSplitStats;
}

void GateScatterSplittingFreeFlightOptrActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);

  // Get user parameters
  fComptonSplittingFactor = DictGetInt(user_info, "compton_splitting_factor");
  fRayleighSplittingFactor = DictGetInt(user_info, "rayleigh_splitting_factor");
  fMaxComptonLevel = DictGetInt(user_info, "max_compton_level");

  // Create the FF operation
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation = new GateGammaFreeFlightOptn("FreeFlightOperation");

  // Create the Compton splitting operation
  l.fComptonSplittingOperation =
      new GateScatterSplittingFreeFlightOptn("ComptonSplittingOperation");
  l.fComptonSplittingOperation->SetSplittingFactor(fComptonSplittingFactor);
  l.fRayleighSplittingOperation =
      new GateScatterSplittingFreeFlightOptn("RayleighSplittingOperation");
  l.fRayleighSplittingOperation->SetSplittingFactor(fRayleighSplittingFactor);

  // Initialize the AA (Angular Acceptance) for the Compton operation
  const auto dd = py::dict(user_info["acceptance_angle"]);
  l.fComptonSplittingOperation->InitializeAAManager(dd);
  l.fRayleighSplittingOperation->InitializeAAManager(dd);
}

void GateScatterSplittingFreeFlightOptrActor::BeginOfRunAction(
    const G4Run *run) {
  if (run->GetRunID() == 0) {
    threadLocal_t &l = threadLocalData.Get();
    l.fSplitStatsPerThread["nb_tracks"] = 0;
    l.fSplitStatsPerThread["nb_tracks_with_free_flight"] = 0;
    l.fSplitStatsPerThread["nb_compt_splits"] = 0;
    l.fSplitStatsPerThread["nb_rayl_splits"] = 0;
    l.fSplitStatsPerThread["nb_killed_non_gamma_particles"] = 0;
    l.fSplitStatsPerThread["nb_killed_gammas_compton_level"] = 0;
    l.fSplitStatsPerThread["nb_killed_gammas_exiting"] = 0;
    l.fSplitStatsPerThread["nb_killed_weight_too_low"] = 0;

    // Check GeneralGammaProcess
    if (G4EmParameters::Instance()->GeneralProcessActive() == false) {
      Fatal("GeneralGammaProcess is not active. This is needed for "
            "ComptonSplittingFreeFlightActor");
    }
  }
}

void GateScatterSplittingFreeFlightOptrActor::BeginOfEventAction(
    const G4Event *event) {
  threadLocal_t &l = threadLocalData.Get();
  l.fComptonInteractionCount = 0;
  l.fCurrentTrackIsFreeFlight = false;
}

void GateScatterSplittingFreeFlightOptrActor::StartTracking(
    const G4Track *track) {
  // A new track is being tracked
  threadLocal_t &l = threadLocalData.Get();
  l.fComptonInteractionCount = 0;
  l.fCurrentTrackIsFreeFlight = false;
  l.fSplitStatsPerThread["nb_tracks"] += 1;

  // If this is the first track, it cannot be free flight.
  if (track->GetTrackID() == 1)
    return;

  // It maybe either:
  // (1) a conventional gamma that we track for Compton
  // or (2) a previous split Compton/Rayleigh scatter that we track with free
  // flight

  // If no creator process (e.g. this is a source event), this is case (1)
  const auto *creator_process = track->GetCreatorProcess();
  if (creator_process == nullptr)
    return;

  // From the wrapped creator process, check if it is a scatter
  const auto *bp =
      dynamic_cast<const G4BiasingProcessInterface *>(creator_process);
  if (IsScatterInteraction(bp) == 0)
    return;

  // We know the creator process was Compt or Rayl, so it is a split gamma.
  l.fCurrentTrackIsFreeFlight = true;
  l.fFreeFlightOperation->ResetInitialTrackWeight(track->GetWeight());

  // debug info
  l.fSplitStatsPerThread["nb_tracks_with_free_flight"] += 1;
}

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
  return nullptr;
}

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // Should we track the particle with free flight or not ?
  const threadLocal_t &l = threadLocalData.Get();
  if (l.fCurrentTrackIsFreeFlight) {

    /*auto step = track->GetStep();
    auto * vol = step->GetPreStepPoint()->GetTouchable()->GetVolume();
    if (vol->GetName() != "phantom_Z") {
      DDD(vol->GetName());
      DDD(track->GetCurrentStepNumber());
    }*/

    return l.fFreeFlightOperation;
  }
  // Conventional tracking
  return nullptr;
}

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // Go in this function every interaction (except Transportation)

  // Check if this is free flight
  threadLocal_t &l = threadLocalData.Get();
  if (l.fCurrentTrackIsFreeFlight) {

    /*auto step = track->GetStep();
    auto * vol = step->GetPreStepPoint()->GetTouchable()->GetVolume();
    if (vol->GetName() != "phantom_Z") {
      DDD(vol->GetName());
      DDD(track->GetCurrentStepNumber());
    }*/
    return callingProcess->GetCurrentOccurenceBiasingOperation();
  }

  // Check if this is a Compton
  int sc = IsScatterInteraction(callingProcess);
  if (sc != 0) {
    // This is a Compton, we split it
    if (sc == 13) {
      l.fComptonInteractionCount++;
      if (l.fComptonInteractionCount <= fMaxComptonLevel) {
        l.fSplitStatsPerThread["nb_compt_splits"] += 1;
        return l.fComptonSplittingOperation;
      }
    }
    // This is a Rayleigh, we split it
    if (sc == 11) {
      l.fSplitStatsPerThread["nb_rayl_splits"] += 1;
      return l.fRayleighSplittingOperation;
    }
  }

  // This is not a Compton
  return callingProcess->GetCurrentOccurenceBiasingOperation();
}

void GateScatterSplittingFreeFlightOptrActor::SteppingAction(G4Step *step) {
  // Go in this function every step, even Transportation
  threadLocal_t &l = threadLocalData.Get();

  if (l.fCurrentTrackIsFreeFlight) {

    /*auto * vol = step->GetPostStepPoint()->GetTouchable()->GetVolume();
    if (vol->GetName() != "phantom_Z") {
      DDD(vol->GetName());
    }*/

    return;
  }

  // if not free flight, we kill the gamma if it exits the volume
  // Exiting the volume is tricky : need to check the post point
  // is in the mother volume.
  if (IsStepExitVolume(step)) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fSplitStatsPerThread["nb_killed_gammas_exiting"] += 1;
    return;
  }

  // if too much Compton, we kill the gamma
  // (cannot be done during ProposeFinalStateBiasingOperation)
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

void GateScatterSplittingFreeFlightOptrActor::EndOfSimulationWorkerAction(
    const G4Run *) {
  G4AutoLock mutex(&StatMutex);
  const threadLocal_t &l = threadLocalData.Get();
  for (const auto &m : l.fSplitStatsPerThread) {
    if (fSplitStats.count(m.first) == 0)
      fSplitStats[m.first] = 0;
    fSplitStats[m.first] += m.second;
  }
}

int GateScatterSplittingFreeFlightOptrActor::IsScatterInteraction(
    const G4BiasingProcessInterface *callingProcess) const {
  // If GammaGeneralProc is used, we need to retrieve the real process within
  // GetSelectedProcess (with SelectedProcess)

  // If GammaGeneralProc is not used, the free flight is not
  // correct when it biases several processes (compt + Rayl + phot + conv).
  // Unsure why.

  if (callingProcess == nullptr)
    return 0;

  // Retrieve the wrapped process
  const auto *wrapped_p = callingProcess->GetWrappedProcess();
  if (wrapped_p == nullptr)
    return 0;

  // We "know" this is a GammaGeneralProcess
  const auto *ggp = dynamic_cast<const G4GammaGeneralProcess *>(wrapped_p);
  if (ggp == nullptr)
    return 0;

  /*
  GetSubProcessName() = compt  GetSubProcessSubType() = 13
  GetSubProcessName() = Rayl   GetSubProcessSubType() = 11
  GetSubProcessName() = phot   GetSubProcessSubType() = 12

  Unsure what it is:
  GetSubProcessName() = GammaGeneralProc  GetSubProcessSubType() = 16
  */
  if (ggp->GetSubProcessSubType() == 13 || ggp->GetSubProcessSubType() == 11)
    return ggp->GetSubProcessSubType();
  return 0;
}
