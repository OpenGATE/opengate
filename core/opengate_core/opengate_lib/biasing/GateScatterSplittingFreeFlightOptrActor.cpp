/* --------------------------------------------------
Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateScatterSplittingFreeFlightOptrActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "G4BiasingProcessInterface.hh"
#include "G4Gamma.hh"
#include "G4GammaGeneralProcess.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "GateScatterSplittingFreeFlightOptn.h"

G4Mutex StatMutex = G4MUTEX_INITIALIZER;

GateScatterSplittingFreeFlightOptrActor::
    GateScatterSplittingFreeFlightOptrActor(py::dict &user_info)
    : GateVBiasOptrActor("ScatterSplittingFreeFlightOperator", user_info,
                         true) {
  fComptonSplittingFactor = 1;
  fRayleighSplittingFactor = 1;
  fMaxComptonLevel = 1;
  fDebug = false;
  fBiasInformation.clear();
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
GateScatterSplittingFreeFlightOptrActor::GetBiasInformation() {
  return fBiasInformation;
}

void GateScatterSplittingFreeFlightOptrActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVBiasOptrActor::InitializeUserInfo(user_info);

  // Get user parameters
  fComptonSplittingFactor = DictGetInt(user_info, "compton_splitting_factor");
  fRayleighSplittingFactor = DictGetInt(user_info, "rayleigh_splitting_factor");
  fMaxComptonLevel = DictGetInt(user_info, "max_compton_level");
  fDebug = DictGetBool(user_info, "debug");
  DDD(fDebug);
  DDD(fDebug);

  // Create the FF operation
  threadLocal_t &l = threadLocalData.Get();
  l.fFreeFlightOperation = new GateGammaFreeFlightOptn("FreeFlightOperation");

  // Create the Compton splitting operation
  l.fComptonSplittingOperation = new GateScatterSplittingFreeFlightOptn(
      "ComptonSplittingOperation",
      &l.fBiasInformationPerThread["nb_compt_tracks"]);
  l.fComptonSplittingOperation->SetSplittingFactor(fComptonSplittingFactor);
  l.fComptonSplittingOperation->fActor = this;

  // Create the Rayleigh splitting operation
  l.fRayleighSplittingOperation = new GateScatterSplittingFreeFlightOptn(
      "RayleighSplittingOperation",
      &l.fBiasInformationPerThread["nb_rayl_tracks"]);
  l.fRayleighSplittingOperation->SetSplittingFactor(fRayleighSplittingFactor);
  l.fRayleighSplittingOperation->fActor = this;

  // Initialize the AA (Angular Acceptance) for the Compton operation
  const auto dd = DictToMap(user_info["angular_acceptance"]);
  l.fComptonSplittingOperation->InitializeAAManager(dd);
  l.fRayleighSplittingOperation->InitializeAAManager(dd);
  l.fComptonSplittingOperation->SetInvolvedBiasActor(this);
  l.fRayleighSplittingOperation->SetInvolvedBiasActor(this);

  // Kill volumes
  fKillVolumes = DictGetVecStr(user_info, "kill_interacting_in_volumes");

  if (G4EmParameters::Instance()->GeneralProcessActive()) {
    Fatal("GeneralGammaProcess is active. Biasing can *not* work for "
          "GateVBiasOptrActor");
  }
}

void GateScatterSplittingFreeFlightOptrActor::BeginOfRunAction(
    const G4Run *run) {
  if (run->GetRunID() == 0) {
    threadLocal_t &l = threadLocalData.Get();
    l.fBiasInformationPerThread["nb_tracks"] = 0;
    l.fBiasInformationPerThread["nb_tracks_with_free_flight"] = 0;
    l.fBiasInformationPerThread["nb_compt_splits"] = 0;
    l.fBiasInformationPerThread["nb_compt_tracks"] = 0;
    l.fBiasInformationPerThread["nb_rayl_splits"] = 0;
    l.fBiasInformationPerThread["nb_rayl_tracks"] = 0;
    l.fBiasInformationPerThread["nb_killed_non_gamma_particles"] = 0;
    l.fBiasInformationPerThread["nb_killed_gammas_compton_level"] = 0;
    l.fBiasInformationPerThread["nb_killed_gammas_exiting"] = 0;
    l.fBiasInformationPerThread["nb_killed_weight_too_low"] = 0;
  }
}

void GateScatterSplittingFreeFlightOptrActor::BeginOfEventAction(
    const G4Event *event) {
  threadLocal_t &l = threadLocalData.Get();
  l.fComptonInteractionCount = 0;
  l.fCurrentTrackIsFreeFlight = false;
}

bool GateScatterSplittingFreeFlightOptrActor::IsFreeFlight(
    const G4Track *track) {
  const auto *track_info =
      static_cast<GateUserTrackInformation *>(track->GetUserInformation());
  if (track_info == nullptr)
    return false;
  if (track_info->GetFirstValue() == fThisIsAFreeFlightTrack)
    return true;
  return false;
}

void GateScatterSplittingFreeFlightOptrActor::StartTracking(
    const G4Track *track) {
  // A new track is being tracked
  threadLocal_t &l = threadLocalData.Get();
  l.fTrackMustBeKilled = false;
  l.fIsStepInExcludedVolume = false;
  l.fLastStepNumber = -1;

  if (fDebug) {
    DDD("\nGateScatterSplittingFreeFlightOptrActor::StartTracking for track ",
        track->GetTrackID(), " to_kill=", l.fTrackMustBeKilled,
        " excluded=", l.fIsStepInExcludedVolume,
        " laststep=", l.fLastStepNumber, " weight=", track->GetWeight(),
        " energy=", track->GetKineticEnergy());
  }

  if (!IsFreeFlight(track)) {
    // this is not an FF or secondary of an FF
    l.fComptonInteractionCount = 0;
    l.fBiasInformationPerThread["nb_tracks"] += 1;
    return;
  }

  // This is an FF
  l.fFreeFlightOperation->ResetInitialTrackWeight(track->GetWeight());
  l.fBiasInformationPerThread["nb_tracks_with_free_flight"] += 1;
}

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track * /* track */,
    const G4BiasingProcessInterface * /* callingProcess */) {
  DDD("MUST NEVER BE HERE");
  Fatal("GateScatterSplittingFreeFlightOptrActor::"
        "ProposeNonPhysicsBiasingOperation");
  threadLocal_t &l = threadLocalData.Get();
  return nullptr;
}

const std::unordered_set<const G4LogicalVolume *> &
GateScatterSplittingFreeFlightOptrActor::GetKillVolumePointers() const {
  threadLocal_t &l = threadLocalData.Get();
  if (!l.fIsKillVolumesCached) {
    BuildLVCache(fKillVolumes, l.fKillVolumePointers,
                 "kill_interacting_in_volumes");
    l.fIsKillVolumesCached = true;
  }
  return l.fKillVolumePointers;
}

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  threadLocal_t &l = threadLocalData.Get();

  if (fDebug) {
    auto p = callingProcess ? callingProcess->GetWrappedProcess() : nullptr;
    G4String procName = p ? p->GetProcessName() : "null";
    DDD("ProposeOccurenceBiasingOperation for track ", track->GetTrackID(),
        " to_kill=", l.fTrackMustBeKilled,
        " excluded=", l.fIsStepInExcludedVolume,
        " laststep=", l.fLastStepNumber, " weight=", track->GetWeight(),
        " energy=", track->GetKineticEnergy(), " process=", procName);
  }

  // ==== CHECK 1 : energy, weight threshold ====
  // Is it a valid particle? (energy or weight cutoff).
  // If not, will be killed in SteppingAction
  if (!IsTrackValid(track)) {
    l.fTrackMustBeKilled = true;
    if (fDebug) {
      DDD("\t fIsTrackValidForStep = false, returning nullptr "
          "(fTrackMustBeKilled=true)");
    }
    return nullptr;
  }
  l.fTrackMustBeKilled = false;

  // ==== CHECK 2 : excluded volumes for parallel world ====
  // Evaluate if the track is within an excluded volume (for parallel world)
  // Note: when there is not parallel world, thit is not useful
  // Note: fLastStepNumber is used to avoid the check for all processes
  const int currentStep = track->GetCurrentStepNumber();
  if (l.fLastStepNumber != currentStep) {
    // Only query the parallel navigator if this is a new step
    // (do not query if this is same step, another process)
    l.fIsStepInExcludedVolume = IsInExcludedVolumeAcrossAllWorlds(track);
    l.fLastStepNumber = currentStep;
    if (fDebug) {
      DDD("\t fIsExcludedForStep=", l.fIsStepInExcludedVolume,
          " laststep=", l.fLastStepNumber);
    }
  }

  // ===========================================================================
  // Cases matrix:
  // - FF + in excluded volume          => analog tracking, NO splitting
  // - FF + not in excluded volume      => FF tracking
  // - FF + kill volume                 => FF tracking
  // - not FF + in excluded volume      => analog but NO splitting
  // - not FF §+ kill volume            => kill particle
  // - not FF + not in excluded volume  => analog, splitting if Compt or Rayl
  // ===========================================================================

  const bool isFF = IsFreeFlight(track);
  if (fDebug) {
    DDD("\t isFF=", isFF);
  }

  // ===========================================================================
  // FF tracking
  if (isFF) {
    if (l.fIsStepInExcludedVolume) {
      // Track is in an unbiased volume (parallel world)
      // Returning nullptr disables FF occurrence, and the cached
      // flag will disable splitting in ProposeFinalState.
      if (fDebug) {
        DDD("\t isFF but excluded, returning nullptr");
      }
      return nullptr;
    }
    if (fDebug) {
      DDD("\t isFF and not excluded, returning FF operation");
    }
    return l.fFreeFlightOperation;
  }

  // ===========================================================================
  // Analog tracking (with possible splitting except if we are in kill volumes)
  if (IsInVolumeListAcrossAllWorlds(track, GetKillVolumePointers())) {
    l.fTrackMustBeKilled = true;
    if (fDebug) {
      DDD("\t no FF and  = false, returning nullptr");
    }
    return nullptr;
  }

  // Conventional, analog tracking
  return nullptr;
}

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // Geant 4 does NOT enter here if the step in "exclude_volumes" or
  // outside the "attached volume"
  // This function is called every interaction except 'Transportation'
  threadLocal_t &l = threadLocalData.Get();

  if (fDebug) {
    auto p = callingProcess ? callingProcess->GetWrappedProcess() : nullptr;
    G4String procName = p ? p->GetProcessName() : "null";
    DDD("ProposeFinalStateBiasingOperation ", procName);
  }

  // Was it valid at the start of the step?
  // Revert to standard physics (no FF, no splitting)
  if (l.fTrackMustBeKilled) {
    if (fDebug) {
      DDD("\t ProposeFinalStateBiasingOperation TrackMustBeKilled=True for "
          "step, returning nullptr");
    }
    return nullptr;
  }

  if (l.fIsStepInExcludedVolume) {
    if (fDebug) {
      DDD("\t ProposeFinalStateBiasingOperation Track in excluded "
          "volume, returning nullptr");
    }
    // Revert to standard physics (no FF, no splitting)
    return nullptr;
  }

  // Is this a FF ?
  if (IsFreeFlight(track)) {
    if (fDebug) {
      DDD("\t ProposeFinalStateBiasingOperation Track is FF, returning "
          "FF operation");
    }
    return l.fFreeFlightOperation;
  }

  // This is not an FF, we may split if Compton or Rayleigh
  const int sc = IsScatterInteraction(callingProcess);
  // This is a Compton, we split it
  if (sc == 13 && fComptonSplittingFactor > 0) {
    // Fixme check compton in Operation to set track status
    l.fComptonInteractionCount++;
    if (l.fComptonInteractionCount <= fMaxComptonLevel) {
      l.fBiasInformationPerThread["nb_compt_splits"] += 1;
      if (fDebug) {
        DDD("\t ProposeFinalStateBiasingOperation Track is Compton, "
            "returning Compton splitting operation");
      }
      return l.fComptonSplittingOperation;
    }
  }
  // This is a Rayleigh, we split it
  if (sc == 11 && fRayleighSplittingFactor > 0) {
    l.fBiasInformationPerThread["nb_rayl_splits"] += 1;
    if (fDebug) {
      DDD("\t ProposeFinalStateBiasingOperation Track is Rayleigh, "
          "returning Rayleigh splitting operation");
    }
    return l.fRayleighSplittingOperation;
  }

  // This is not a Compton nor a Rayleigh
  if (fDebug) {
    DDD("\t ProposeFinalStateBiasingOperation Track is not compt nor "
        "rayl, returning ????");
  }
  return callingProcess
      ->GetCurrentFinalStateBiasingOperation(); // FIXME or nullptr ?
}

void GateScatterSplittingFreeFlightOptrActor::SteppingAction(G4Step *step) {
  // G4 do NOT enter here if the step is outside the "attached volume"
  // (but this is usually the world), but do enter if in "exclude_volumes"
  // (Go in this function every step, even Transportation)
  threadLocal_t &l = threadLocalData.Get();

  if (fDebug) {
    DDD("GateScatterSplittingFreeFlightOptrActor::SteppingAction for track ",
        step->GetTrack()->GetTrackID(), " to_kill=", l.fTrackMustBeKilled,
        " excluded=", l.fIsStepInExcludedVolume,
        " laststep=", l.fLastStepNumber,
        " weight=", step->GetTrack()->GetWeight(),
        " energy=", step->GetTrack()->GetKineticEnergy());
  }

  if (l.fTrackMustBeKilled) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    // l.fTrackMustBeKilled = false; // FIXME not needed ?
    if (fDebug) {
      DDD("\t Track not valid for step, killing track and returning");
    }
    return;
  }

  // Check if this is a free flight. If yes, we do nothing.
  // FF tracks this particle except if it is in an unbiased volume.
  // This is managed by Optr/Optn Geant4 biasing logic EXCEPT if
  // the track is in parallel world.
  const bool isFF = IsFreeFlight(step->GetTrack());
  if (isFF) {
    if (fDebug) {
      DDD("\t isFF, letting track continue");
    }
    return;
  }

  // When it is NOT a FF particle, we check against ALL worlds (Mass and
  // Parallel) To kill the particle if it enters a KillingVolume
  if (IsStepEnteringVolumeAcrossAllWorlds(step, GetKillVolumePointers())) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fBiasInformationPerThread["nb_killed_gammas_exiting"] += 1;
    if (fDebug) {
      DDD("\t Track entering parallel/mass kill volume, killing track and "
          "returning");
    }
    return;
  }

  // if too much Compton, we also kill the gamma
  // (cannot be done during ProposeFinalStateBiasingOperation)
  if (l.fComptonInteractionCount > fMaxComptonLevel) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fBiasInformationPerThread["nb_killed_gammas_compton_level"] += 1;
    // FIXME Rayl after Compt ?
    return;
  }

  // keep only gamma
  if (step->GetTrack()->GetDefinition() != G4Gamma::Gamma()) {
    // kill it without mercy
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fBiasInformationPerThread["nb_killed_non_gamma_particles"] += 1;
  }
}

void GateScatterSplittingFreeFlightOptrActor::EndOfSimulationWorkerAction(
    const G4Run *) {
  G4AutoLock mutex(&StatMutex);
  const threadLocal_t &l = threadLocalData.Get();
  for (const auto &m : l.fBiasInformationPerThread) {
    if (fBiasInformation.count(m.first) == 0)
      fBiasInformation[m.first] = 0;
    fBiasInformation[m.first] += m.second;
  }
}

int GateScatterSplittingFreeFlightOptrActor::
    IsScatterInteractionGeneralProcess_OLD(
        const G4BiasingProcessInterface *callingProcess) {
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
  GetSubProcessName() = GammaGeneralProc GetSubProcessSubType() = 16
  */

  return ggp->GetSubProcessSubType();
}

int GateScatterSplittingFreeFlightOptrActor::IsScatterInteraction(
    const G4BiasingProcessInterface *callingProcess) {
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

  /*
  GetProcessName() = compt  GetProcessSubType() = 13
  GetProcessName() = Rayl   GetProcessSubType() = 11
  GetProcessName() = phot   GetProcessSubType() = 12
  */

  return wrapped_p->GetProcessSubType();
}
