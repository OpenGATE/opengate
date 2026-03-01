/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChannelXSScalingOptrActor_h
#define GateChannelXSScalingOptrActor_h

#include "GateVBiasOptrActor.h"

#include <map>
#include <utility>
#include <vector>

#include "G4BOptnChangeCrossSection.hh"
#include "G4BiasingProcessInterface.hh"
#include "G4Step.hh"

/**
 * GateChannelXSScalingOptrActor
 *
 * Scales the alphaInelastic cross section by xs_scaling and applies
 * channel-selective rejection sampling with no weight manipulation:
 *
 *   - Desired channel: the interaction is accepted as physical reality.
 *     Secondaries are kept exactly as Geant4 produced them; no weight is
 *     touched.  The channel fires xs_scaling × f_C times more often.
 *
 *   - Unwanted channels: Russian roulette preserves their natural rate.
 *     Because alphaInelastic fires xs_scaling × more often, each unwanted
 *     event is accepted with probability 1/xs_scaling (kept as-is) and
 *     rolled back with probability 1 − 1/xs_scaling.
 *     Net unwanted rate = xs_scaling × (1−f_C) × (1/xs_scaling) = (1−f_C) ✓
 *     On rollback: all secondaries are killed and the primary alpha is
 *     returned to its exact pre-interaction state (position, momentum,
 *     energy, times, weight, geometry/touchable); it then continues normally.
 *
 * All changes are purely physical: the cross section is scaled, desired
 * events are enhanced, unwanted events remain at their natural rate.
 * No statistical weights are introduced or modified.
 *
 * Note: Geant4's G4BOptnChangeCrossSection automatically applies w × 1/xs_scaling
 * to the primary when the biasing fires.  Desired-channel secondaries therefore
 * inherit this factor.  For counting-based cross-section analysis this is
 * irrelevant; for weighted scoring (DoseActor, etc.) callers should be aware
 * of it.  Unwanted-channel rollbacks are fully clean: the primary weight is
 * restored from the pre-step point (= original value before biasing fired).
 *
 * No warmup run is needed; xs_scaling is the direct multiplier on the total
 * alphaInelastic cross section.
 */
class GateChannelXSScalingOptrActor : public GateVBiasOptrActor {
public:
  explicit GateChannelXSScalingOptrActor(py::dict &user_info);
  ~GateChannelXSScalingOptrActor() override;

  void InitializeCpp() override;
  void InitializeUserInfo(py::dict &user_info) override;

  G4VBiasingOperation *
  ProposeOccurenceBiasingOperation(const G4Track *track,
                                   const G4BiasingProcessInterface *callingProcess) override;

  G4VBiasingOperation *
  ProposeNonPhysicsBiasingOperation(const G4Track *track,
                                    const G4BiasingProcessInterface *callingProcess) override;

  G4VBiasingOperation *
  ProposeFinalStateBiasingOperation(const G4Track *track,
                                    const G4BiasingProcessInterface *callingProcess) override;

  void SteppingAction(G4Step *step) override;
  void StartTracking(const G4Track *track) override;
  void EndOfRunAction(const G4Run *run) override;

  // Sorted vector of (Z, A) pairs identifying a nuclear reaction channel
  using ChannelSig = std::vector<std::pair<int, int>>;

private:
  double fXSScaling = 1.0;
  ChannelSig fDesiredChannel;

  // One biasing operation per biasing-process interface (GB01 pattern)
  std::map<const G4BiasingProcessInterface *, G4BOptnChangeCrossSection *> fChangeXSOperations;

  // Per-track: whether exponential law has been sampled yet for each process
  std::map<const G4BiasingProcessInterface *, bool> fOpSampledForThisTrack;

  // Prevent multiple UpdateForStep() calls within the same Geant4 step
  std::map<const G4BiasingProcessInterface *, int> fLastStepNumberUpdated;

  bool IsAlphaInelastic(const G4BiasingProcessInterface *p) const;

  G4BOptnChangeCrossSection *
  GetOrCreateChangeXSOperation(const G4BiasingProcessInterface *callingProcess);

  G4double GetAnalogMacroscopicXS(const G4Track *track,
                                  const G4BiasingProcessInterface *callingProcess) const;

  // Build a sorted (Z,A) signature from the step's secondaries (+surviving primary)
  static ChannelSig BuildChannelSig(const G4Step *step);

  // Roll back the step: kill secondaries, restore primary to pre-step state
  static void RollbackStep(G4Step *step);
};

#endif
