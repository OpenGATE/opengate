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
  for (auto &name : fKillVolumes) {
    const auto *v = G4LogicalVolumeStore::GetInstance()->GetVolume(name);
    fKillLogicalVolumes.push_back(v);
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

    // Check if GeneralGammaProcess is disabled
    if (G4EmParameters::Instance()->GeneralProcessActive()) {
      Fatal("GeneralGammaProcess is active. This do *not* work for "
            "ScatterSplittingFreeFlightActor");
    }
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
  l.fIsTrackValidForStep = true;

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

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  threadLocal_t &l = threadLocalData.Get();

  // Is it a valid particle?
  if (!IsTrackValid(track)) {
    l.fIsTrackValidForStep = false;
    return nullptr;
  }
  l.fIsTrackValidForStep = true;

  if (IsFreeFlight(track)) {
    return l.fFreeFlightOperation;
  }
  return nullptr;
}

G4VBiasingOperation *
GateScatterSplittingFreeFlightOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  // Geant 4 does NOT enter here if the step in "exclude_volumes" or
  // outside the "attached volume"
  // This function is called every interaction except 'Transportation'
  threadLocal_t &l = threadLocalData.Get();

  // Was it valid at the start of the step?
  if (!l.fIsTrackValidForStep)
    return nullptr;

  // If the weight is not 1, this is a FF
  if (IsFreeFlight(track)) {
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
      return l.fComptonSplittingOperation;
    }
  }
  // This is a Rayleigh, we split it
  if (sc == 11 && fRayleighSplittingFactor > 0) {
    l.fBiasInformationPerThread["nb_rayl_splits"] += 1;
    return l.fRayleighSplittingOperation;
  }

  // This is not a Compton nor a Rayleigh
  return callingProcess
      ->GetCurrentFinalStateBiasingOperation(); // FIXME or nullptr ?
}

void GateScatterSplittingFreeFlightOptrActor::SteppingAction(G4Step *step) {
  // G4 do NOT enter here if the step is outside the "attached volume"
  // (but this is usually the world), but do enter if in "exclude_volumes"
  // (Go in this function every step, even Transportation)
  threadLocal_t &l = threadLocalData.Get();

  if (!l.fIsTrackValidForStep) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fIsTrackValidForStep = true;
    return;
  }

  // Check if this is a free flight. If yes, we do nothing.
  // FF tracks this particle except if it is in an unbiased volume.
  // This is managed by Optr/Optn Geant4 biasing logic.
  if (IsFreeFlight(step->GetTrack())) {
    return;
  }

  // if this is not a free flight, we kill the gamma when it enters some defined
  // volumes
  if (IsStepEnteringVolume(step, fKillLogicalVolumes)) {
    step->GetTrack()->SetTrackStatus(fStopAndKill);
    l.fBiasInformationPerThread["nb_killed_gammas_exiting"] += 1;
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
