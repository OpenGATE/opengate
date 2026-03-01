/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateChannelXSScalingOptrActor.h"

#include "../GateHelpers.h"
#include "../GateHelpersDict.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <set>
#include <sstream>

#include "G4ForceCondition.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4Track.hh"
#include "G4TrackStatus.hh"
#include "G4TransportationManager.hh"
#include "G4VProcess.hh"
#include "Randomize.hh"

using ChannelSig = GateChannelXSScalingOptrActor::ChannelSig;

// Debug counters (printed at end of run)
static std::atomic<int> sDbgTotal{0};
static std::atomic<int> sDbgDesired{0};
static std::atomic<int> sDbgRollback{0};

// ---------------------------------------------------------------------------
GateChannelXSScalingOptrActor::GateChannelXSScalingOptrActor(py::dict &user_info)
    : GateVBiasOptrActor("GateChannelXSScalingOptrActor", user_info, true) {
  fActions.insert("SteppingAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("EndOfRunAction");
}

GateChannelXSScalingOptrActor::~GateChannelXSScalingOptrActor() {
  for (auto &kv : fChangeXSOperations) {
    delete kv.second;
    kv.second = nullptr;
  }
  fChangeXSOperations.clear();
  fOpSampledForThisTrack.clear();
  fLastStepNumberUpdated.clear();
}

// ---------------------------------------------------------------------------
void GateChannelXSScalingOptrActor::InitializeCpp() {
  // Nothing to reset for this actor (no shared warmup state)
}

// ---------------------------------------------------------------------------
void GateChannelXSScalingOptrActor::InitializeUserInfo(py::dict &user_info) {
  GateVBiasOptrActor::InitializeUserInfo(user_info);

  fXSScaling = DictGetDouble(user_info, "xs_scaling");
  if (fXSScaling <= 0.0) {
    Fatal("GateChannelXSScalingOptrActor: xs_scaling must be > 0");
  }

  auto rawChannel = DictGetVecofVecDouble(user_info, "desired_channel");
  fDesiredChannel.clear();
  for (const auto &pair : rawChannel) {
    if (pair.size() >= 2) {
      fDesiredChannel.push_back({static_cast<int>(pair[0]),
                                  static_cast<int>(pair[1])});
    }
  }
  std::sort(fDesiredChannel.begin(), fDesiredChannel.end());
}

// ---------------------------------------------------------------------------
bool GateChannelXSScalingOptrActor::IsAlphaInelastic(
    const G4BiasingProcessInterface *p) const {
  if (!p) return false;
  auto *wp = p->GetWrappedProcess();
  if (!wp) return false;
  return (wp->GetProcessName() == "alphaInelastic");
}

// ---------------------------------------------------------------------------
G4VBiasingOperation *
GateChannelXSScalingOptrActor::ProposeNonPhysicsBiasingOperation(
    const G4Track *, const G4BiasingProcessInterface *) {
  return nullptr;
}

G4VBiasingOperation *
GateChannelXSScalingOptrActor::ProposeFinalStateBiasingOperation(
    const G4Track *, const G4BiasingProcessInterface *) {
  return nullptr;
}

// ---------------------------------------------------------------------------
G4BOptnChangeCrossSection *
GateChannelXSScalingOptrActor::GetOrCreateChangeXSOperation(
    const G4BiasingProcessInterface *callingProcess) {
  auto it = fChangeXSOperations.find(callingProcess);
  if (it != fChangeXSOperations.end()) return it->second;

  std::ostringstream name;
  name << "ChannelXSScaling_"
       << std::hex << reinterpret_cast<std::uintptr_t>(callingProcess);

  auto *op = new G4BOptnChangeCrossSection(name.str());
  fChangeXSOperations[callingProcess] = op;
  fOpSampledForThisTrack[callingProcess] = false;
  fLastStepNumberUpdated[callingProcess] = -1;
  return op;
}

// ---------------------------------------------------------------------------
G4double GateChannelXSScalingOptrActor::GetAnalogMacroscopicXS(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) const {
  auto *wrapped = callingProcess ? callingProcess->GetWrappedProcess() : nullptr;
  if (!wrapped) return 0.0;

  G4double lambda = wrapped->GetCurrentInteractionLength();
  if (lambda <= 0.0) {
    G4ForceCondition cond = NotForced;
    lambda = wrapped->PostStepGetPhysicalInteractionLength(*track, 0.0, &cond);
  }
  if (lambda <= 0.0) return 0.0;
  return 1.0 / lambda;
}

// ---------------------------------------------------------------------------
void GateChannelXSScalingOptrActor::StartTracking(const G4Track *) {
  for (auto &kv : fOpSampledForThisTrack) kv.second = false;
  for (auto &kv : fLastStepNumberUpdated) kv.second = -1;
}

// ---------------------------------------------------------------------------
G4VBiasingOperation *GateChannelXSScalingOptrActor::ProposeOccurenceBiasingOperation(
    const G4Track *track, const G4BiasingProcessInterface *callingProcess) {
  if (!IsTrackValid(track)) return nullptr;
  if (track->GetDefinition()->GetParticleName() != "alpha") return nullptr;
  if (!IsAlphaInelastic(callingProcess)) return nullptr;
  if (std::abs(fXSScaling - 1.0) < 1e-12) return nullptr;

  auto *op = GetOrCreateChangeXSOperation(callingProcess);
  if (!op) return nullptr;

  const G4double xs_unbiased = GetAnalogMacroscopicXS(track, callingProcess);
  if (xs_unbiased <= 0.0) return nullptr;

  op->SetBiasedCrossSection(fXSScaling * xs_unbiased, true);

  auto &sampled = fOpSampledForThisTrack[callingProcess];
  auto &lastStepUpdated = fLastStepNumberUpdated[callingProcess];
  const int stepNo = track->GetCurrentStepNumber();

  if (!sampled) {
    op->Sample();
    sampled = true;
    lastStepUpdated = stepNo;
    return op;
  }

  if (stepNo == lastStepUpdated) return op;

  // New step: update or re-sample the interaction law
  if (op->GetInteractionOccured()) {
    op->Sample();
  } else {
    const G4double prev = callingProcess->GetPreviousStepSize();
    if (prev > 0.0) op->UpdateForStep(prev);
  }
  lastStepUpdated = stepNo;
  return op;
}

// ---------------------------------------------------------------------------
// Build a sorted (Z,A) channel signature from the surviving primary and
// all secondaries produced in this step.
// ---------------------------------------------------------------------------
ChannelSig GateChannelXSScalingOptrActor::BuildChannelSig(const G4Step *step) {
  ChannelSig sig;

  // Include only hadronic/nuclear particles (Z>0 or A>0).
  // Neutrons have Z=0, A=1 so they pass.  Gammas, electrons, etc. have Z=A=0.
  auto isNuclear = [](const G4ParticleDefinition *def) -> bool {
    return (static_cast<int>(def->GetAtomicNumber()) > 0 ||
            static_cast<int>(def->GetAtomicMass()) > 0);
  };

  const auto *track = step->GetTrack();
  if (track->GetTrackStatus() != fStopAndKill) {
    const auto *def = track->GetDefinition();
    if (isNuclear(def)) {
      sig.push_back({static_cast<int>(def->GetAtomicNumber()),
                     static_cast<int>(def->GetAtomicMass())});
    }
  }

  const auto *secondaries = step->GetSecondaryInCurrentStep();
  if (secondaries) {
    for (const auto *sec : *secondaries) {
      const auto *def = sec->GetDefinition();
      if (isNuclear(def)) {
        sig.push_back({static_cast<int>(def->GetAtomicNumber()),
                       static_cast<int>(def->GetAtomicMass())});
      }
    }
  }

  std::sort(sig.begin(), sig.end());
  return sig;
}

// ---------------------------------------------------------------------------
// Roll back the primary alpha to its exact pre-step state and kill all
// secondaries produced by the unwanted interaction.
//
// Why the post-step point must also be restored:
//   G4SteppingManager::Stepping() starts each call with
//     fStep->CopyPostToPreStepPoint()
//   so the post-step point of this step becomes the pre-step point of the
//   next step.  If we only restore the track but leave the post-step point
//   at the interaction vertex, the next step would begin from the wrong
//   position and the geometry/navigation state would be inconsistent.
//
// Why SetNextTouchableHandle:
//   At the beginning of each Stepping() call, G4SteppingManager does
//     fTrack->SetTouchableHandle(fTrack->GetNextTouchableHandle())
//   By restoring the next-touchable to the pre-step volume, the navigation
//   state is consistent with the restored position.
// ---------------------------------------------------------------------------
void GateChannelXSScalingOptrActor::RollbackStep(G4Step *step) {
  const G4StepPoint *pre = step->GetPreStepPoint();
  G4StepPoint *post = step->GetPostStepPoint();

  // Remove the secondaries produced in this step.
  //
  // APPROACH: delete the G4Track objects directly and erase them from the
  // step's cumulative secondary vector (fSecondary, which is the same object
  // returned by G4TrackingManager::GimmeSecondaries()).  This ensures the
  // rolled-back secondaries are never handed to G4StackManager and never
  // take a step, regardless of any track-status routing.
  //
  // Setting fKillTrackAndSecondaries was tried but the tracks still appeared
  // in ROOT output, presumably because the stacking manager routes them to
  // the urgent stack before the status can prevent stepping.
  auto *allSecs = step->GetfSecondary();
  const auto *curSecs = step->GetSecondaryInCurrentStep();
  if (curSecs && allSecs && !curSecs->empty()) {
    // Delete the G4Track objects and erase them from the cumulative secondary
    // vector (fSecondary = GimmeSecondaries()).  This ensures rolled-back
    // secondaries are never handed to G4StackManager.
    for (const auto *sec : *curSecs) {
      delete const_cast<G4Track *>(sec);
    }
    const std::size_t nCur = curSecs->size();
    if (allSecs->size() >= nCur) {
      allSecs->resize(allSecs->size() - nCur);
    }
  }

  // Restore the post-step point to pre-step values so CopyPostToPreStepPoint
  // correctly seeds the next step from the pre-interaction position.
  post->SetPosition(pre->GetPosition());
  post->SetKineticEnergy(pre->GetKineticEnergy());
  post->SetMomentumDirection(pre->GetMomentumDirection());
  post->SetGlobalTime(pre->GetGlobalTime());
  post->SetLocalTime(pre->GetLocalTime());
  post->SetProperTime(pre->GetProperTime());
  post->SetWeight(pre->GetWeight());
  post->SetTouchableHandle(pre->GetTouchableHandle());

  // Restore the primary track itself
  auto *track = const_cast<G4Track *>(step->GetTrack());
  track->SetPosition(pre->GetPosition());
  track->SetKineticEnergy(pre->GetKineticEnergy());
  track->SetMomentumDirection(pre->GetMomentumDirection());
  track->SetGlobalTime(pre->GetGlobalTime());
  track->SetLocalTime(pre->GetLocalTime());
  track->SetWeight(pre->GetWeight());
  track->SetNextTouchableHandle(pre->GetTouchableHandle());
  track->SetTrackStatus(fAlive);

  // Re-sync the navigator with the restored position.
  //
  // G4Transportation::AlongStepDoIt() updates the navigator's internal
  // position to the interaction vertex (post-step point) during each step.
  // After we roll the track back to the pre-step point, the navigator is
  // out of sync by ~1 step length, which triggers GeomNav1002 warnings and
  // can cause incorrect boundary detection in the next step.
  //
  // LocateGlobalPointWithinVolume() is the lightweight update path: it
  // resets the navigator's cached position without traversing the geometry
  // hierarchy.  Both the pre-step and post-step points are guaranteed to be
  // inside the same volume (the actor's attached volume), so this is safe.
  G4TransportationManager::GetTransportationManager()
      ->GetNavigatorForTracking()
      ->LocateGlobalPointWithinVolume(pre->GetPosition());
}

// ---------------------------------------------------------------------------
void GateChannelXSScalingOptrActor::SteppingAction(G4Step *step) {
  if (!step) return;

  const auto *track = step->GetTrack();
  if (!track) return;

  if (track->GetDefinition()->GetParticleName() != "alpha") return;

  const auto *post = step->GetPostStepPoint();
  if (!post) return;

  const auto *proc = post->GetProcessDefinedStep();
  if (!proc) return;

  // G4GenericBiasingPhysics wraps the process; the wrapper name is
  // "biasWrapper(alphaInelastic)".  A substring match covers both cases.
  if (proc->GetProcessName().find("alphaInelastic") == std::string::npos) return;

  if (fDesiredChannel.empty()) return;

  const ChannelSig sig = BuildChannelSig(step);

  // Desired channel check: every required (Z,A) pair must appear at least
  // once in sig.  Extra particles in sig are ignored — the user specifies a
  // minimum set of required products, not an exact final state.
  bool isDesired = true;
  for (const auto &req : fDesiredChannel) {
    if (std::find(sig.begin(), sig.end(), req) == sig.end()) {
      isDesired = false;
      break;
    }
  }

  ++sDbgTotal;
  if (isDesired) {
    // -----------------------------------------------------------------------
    // Desired channel: accept as physical reality — nothing to do.
    // The interaction occurred at the scaled rate; the secondaries are real
    // particles.  No weight manipulation is applied.
    // -----------------------------------------------------------------------
    ++sDbgDesired;
  } else {
    // -----------------------------------------------------------------------
    // Unwanted channel: Russian roulette to preserve the natural rate.
    //
    // alphaInelastic fires xs_scaling × more often due to the biased XS.
    // To keep the net rate of unwanted channels at the unbiased value we
    // accept them with probability 1/xs_scaling and roll back the rest:
    //
    //   accepted rate = xs_scaling × (1-f_C) × (1/xs_scaling) = (1-f_C)  ✓
    //
    // This leaves the desired channel enhanced by xs_scaling while unwanted
    // channels appear at exactly their natural rate — no weights involved.
    // -----------------------------------------------------------------------
    if (G4UniformRand() * fXSScaling > 1.0) {
      ++sDbgRollback;
      RollbackStep(step);
    }
  }
}

// ---------------------------------------------------------------------------
void GateChannelXSScalingOptrActor::EndOfRunAction(const G4Run *) {
  std::cout << "\n[ChannelXSScaling] End-of-run summary:\n"
            << "  Total alphaInelastic (in target)  : " << sDbgTotal.load() << "\n"
            << "  Desired channel (subset match)    : " << sDbgDesired.load() << "\n"
            << "  Unwanted channel                  : "
            << sDbgTotal.load() - sDbgDesired.load() << "\n"
            << "  Rolled back (Russian roulette)    : " << sDbgRollback.load() << "\n";
}
