/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateChannelSelectiveWrapper.h"

#include <algorithm>
#include <cmath>
#include <iostream>

#include "G4Alpha.hh"
#include "G4ForceCondition.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4TrackStatus.hh"
#include "G4VParticleChange.hh"
#include "Randomize.hh"

// ── Static counters ──────────────────────────────────────────────────────────
std::atomic<int> GateChannelSelectiveWrapper::sTotal{0};
std::atomic<int> GateChannelSelectiveWrapper::sDesired{0};
std::atomic<int> GateChannelSelectiveWrapper::sRollback{0};

// ── GateChannelSelectiveWrapper ──────────────────────────────────────────────

GateChannelSelectiveWrapper::GateChannelSelectiveWrapper(
    G4VProcess *wrappedProcess, G4double xsScaling,
    const std::vector<std::vector<int>> &desiredChannel)
    : G4WrapperProcess("ChannelSelectiveWrapper_" +
                           (wrappedProcess ? wrappedProcess->GetProcessName()
                                           : G4String("unknown")),
                       wrappedProcess ? wrappedProcess->GetProcessType()
                                      : fHadronic),
      fXSScaling(xsScaling) {
  if (wrappedProcess) RegisterProcess(wrappedProcess);

  for (const auto &pair : desiredChannel) {
    if (pair.size() >= 2)
      fDesiredChannel.push_back({pair[0], pair[1]});
  }
  std::sort(fDesiredChannel.begin(), fDesiredChannel.end());
}

GateChannelSelectiveWrapper::~GateChannelSelectiveWrapper() = default;

// ---------------------------------------------------------------------------
void GateChannelSelectiveWrapper::ResetCounts() {
  sTotal    = 0;
  sDesired  = 0;
  sRollback = 0;
}

// ---------------------------------------------------------------------------
G4double GateChannelSelectiveWrapper::PostStepGetPhysicalInteractionLength(
    const G4Track &track, G4double previousStepSize,
    G4ForceCondition *condition) {
  // The wrapped G4HadronicProcess decrements its internal NILL (Number of
  // Interaction Lengths Left) by previousStepSize / MFP_true each step, and
  // returns NILL × MFP_true.  We divide by fXSScaling, so G4 sees:
  //   PIL = NILL × MFP_true / xs_scaling = NILL × MFP_eff
  //
  // For the process to fire xs_scaling× more often, PIL must decrease at
  // −1 mm per mm of path (the correct rate for a process with MFP = MFP_eff).
  // Passing the raw previousStepSize would make NILL decrement at only
  // 1/xs_scaling of the correct rate.
  //
  // Fix: multiply previousStepSize by fXSScaling before forwarding.  This
  // forces NILL to deplete at previousStepSize / MFP_eff, so the process
  // fires with the intended mean free path of MFP_eff = MFP_true / xs_scaling.
  //
  // Note: after any DoIt call G4HadronicProcess sets NILL = −1 automatically,
  // so a fresh sample is always drawn on the next PSGETPIL call regardless of
  // the value of previousStepSize passed here.
  const G4double mfp =
      G4WrapperProcess::PostStepGetPhysicalInteractionLength(
          track, previousStepSize * fXSScaling, condition);

  if (mfp <= 0.0 || std::isinf(mfp) || std::isnan(mfp)) return mfp;
  return mfp / fXSScaling;
}

// ---------------------------------------------------------------------------
G4VParticleChange *
GateChannelSelectiveWrapper::PostStepDoIt(const G4Track &track,
                                           const G4Step &step) {
  // Let the wrapped hadronic process generate the full final state.
  G4VParticleChange *pc = G4WrapperProcess::PostStepDoIt(track, step);

  if (!pc || fDesiredChannel.empty()) return pc;

  const ChannelSig sig = BuildChannelSig(pc, &track);
  const bool isDesired = IsDesiredChannel(sig);

  ++sTotal;

  if (isDesired) {
    ++sDesired;
    return pc;  // Accept; alpha and secondaries continue as real physics.
  }

  // Unwanted channel: Russian roulette preserves the natural rate.
  //   biased rate  = xs_scaling × (1 − f_C) × natural_rate
  //   accept prob  = 1 / xs_scaling
  //   net rate     = (1 − f_C) × natural_rate  ✓
  if (G4UniformRand() * fXSScaling <= 1.0) {
    return pc;  // Accepted unwanted — rate preserved, no weights touched.
  }

  // Rejected: clean up secondaries to avoid memory leaks.
  ++sRollback;
  const G4int nSec = pc->GetNumberOfSecondaries();
  for (G4int i = 0; i < nSec; ++i) {
    delete pc->GetSecondary(i);
  }
  pc->Initialize(track);

  // Return "no hadronic interaction occurred": alpha continues from its
  // post-step position unchanged.  No weights modified.
  fNullChange.Initialize(track);
  return &fNullChange;
}

// ---------------------------------------------------------------------------
// static
GateChannelSelectiveWrapper::ChannelSig
GateChannelSelectiveWrapper::BuildChannelSig(const G4VParticleChange *pc,
                                              const G4Track *track) {
  ChannelSig sig;

  // Include only nuclear/hadronic particles (Z > 0 or A > 0).
  // Neutrons: Z=0, A=1 → included.  Photons/leptons: Z=A=0 → excluded.
  auto isNuclear = [](const G4ParticleDefinition *def) -> bool {
    return (static_cast<int>(def->GetAtomicNumber()) > 0 ||
            static_cast<int>(def->GetAtomicMass()) > 0);
  };

  // Primary track if it survives the interaction.
  if (pc->GetTrackStatus() != fStopAndKill) {
    const auto *def = track->GetDefinition();
    if (isNuclear(def))
      sig.push_back({static_cast<int>(def->GetAtomicNumber()),
                     static_cast<int>(def->GetAtomicMass())});
  }

  // Secondaries produced by the hadronic model.
  const G4int nSec = pc->GetNumberOfSecondaries();
  for (G4int i = 0; i < nSec; ++i) {
    const G4Track *sec = pc->GetSecondary(i);
    if (!sec) continue;
    const auto *def = sec->GetDefinition();
    if (isNuclear(def))
      sig.push_back({static_cast<int>(def->GetAtomicNumber()),
                     static_cast<int>(def->GetAtomicMass())});
  }

  std::sort(sig.begin(), sig.end());
  return sig;
}

// ---------------------------------------------------------------------------
bool GateChannelSelectiveWrapper::IsDesiredChannel(
    const ChannelSig &sig) const {
  for (const auto &req : fDesiredChannel) {
    if (std::find(sig.begin(), sig.end(), req) == sig.end()) return false;
  }
  return true;
}

// ── GateChannelSelectiveWrapperPhysics ───────────────────────────────────────

GateChannelSelectiveWrapperPhysics::GateChannelSelectiveWrapperPhysics(
    G4double xsScaling, const std::vector<std::vector<int>> &desiredChannel)
    : G4VPhysicsConstructor("GateChannelSelectiveWrapperPhysics"),
      fXSScaling(xsScaling), fDesiredChannel(desiredChannel) {}

// ---------------------------------------------------------------------------
void GateChannelSelectiveWrapperPhysics::ConstructProcess() {
  // Find the alpha particle.
  G4ParticleDefinition *alpha =
      G4ParticleTable::GetParticleTable()->FindParticle("alpha");
  if (!alpha) {
    G4Exception("GateChannelSelectiveWrapperPhysics::ConstructProcess",
                "Gate0100", FatalException,
                "Alpha particle not found in particle table.");
    return;
  }

  G4ProcessManager *pm = alpha->GetProcessManager();
  if (!pm) {
    G4Exception("GateChannelSelectiveWrapperPhysics::ConstructProcess",
                "Gate0101", FatalException,
                "G4ProcessManager for alpha is null.");
    return;
  }

  // Find alphaInelastic in the alpha's process list.
  G4VProcess *target = nullptr;
  G4ProcessVector *pvec = pm->GetProcessList();
  for (std::size_t i = 0; i < static_cast<std::size_t>(pvec->size()); ++i) {
    G4VProcess *p = (*pvec)[i];
    if (p && p->GetProcessName() == "alphaInelastic") {
      target = p;
      break;
    }
  }

  if (!target) {
    G4Exception("GateChannelSelectiveWrapperPhysics::ConstructProcess",
                "Gate0102", FatalException,
                "alphaInelastic process not found for alpha. "
                "Ensure the base physics list is set before registering "
                "GateChannelSelectiveWrapperPhysics.");
    return;
  }

  // Wrap the existing process and replace it.
  // G4ProcessManager::RemoveProcess does NOT delete the process object —
  // the wrapper holds a reference to it and calls its DoIt methods.
  auto *wrapper = new GateChannelSelectiveWrapper(target, fXSScaling,
                                                   fDesiredChannel);
  pm->RemoveProcess(target);
  pm->AddDiscreteProcess(wrapper);
}
