/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChannelSelectiveWrapper_h
#define GateChannelSelectiveWrapper_h

#include <atomic>
#include <utility>
#include <vector>

#include "G4ParticleChange.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4WrapperProcess.hh"

// ---------------------------------------------------------------------------
/**
 * GateChannelSelectiveWrapper
 *
 * Wraps an existing hadronic process (typically alphaInelastic) and provides
 * channel-selective cross-section scaling with no statistical weights:
 *
 *  1. The total process XS is multiplied by xs_scaling so that the process
 *     fires xs_scaling× more often.  This is achieved by dividing the mean
 *     free path returned to G4 by xs_scaling in
 *     PostStepGetPhysicalInteractionLength.
 *
 *  2. When the wrapped process fires and produces a final state, the reaction
 *     channel is identified from the secondaries:
 *       - Desired channel  → accepted as physical reality; returned unchanged.
 *       - Unwanted channel → Russian roulette at 1/xs_scaling acceptance.
 *         Accepted:  returned unchanged (natural rate preserved on average).
 *         Rejected:  secondary G4Track objects are deleted; a null particle
 *                    change is returned so the primary continues unaffected
 *                    from its post-step position.
 *
 * No particle weights are touched at any point.  DoseActor, PhaseSpaceActor,
 * and all other scoring infrastructure see a physically correct simulation.
 *
 * Registered via GateChannelSelectiveWrapperPhysics (see below), which is a
 * G4VPhysicsConstructor that finds the existing alphaInelastic process on the
 * alpha's G4ProcessManager and swaps it for this wrapper.
 */
class GateChannelSelectiveWrapper : public G4WrapperProcess {
public:
  using ChannelSig = std::vector<std::pair<int, int>>;

  GateChannelSelectiveWrapper(G4VProcess *wrappedProcess, G4double xsScaling,
                               const std::vector<std::vector<int>> &desiredChannel);
  ~GateChannelSelectiveWrapper() override;

  // Scale the mean free path so the process fires xs_scaling× more often.
  // Delegating to the wrapped process's GPIL also initialises its internal
  // cross-section state, which PostStepDoIt relies upon.
  G4double PostStepGetPhysicalInteractionLength(const G4Track &track,
                                                G4double previousStepSize,
                                                G4ForceCondition *condition) override;

  // Let the wrapped process generate the full hadronic final state, then
  // apply channel selection and return the appropriate particle change.
  G4VParticleChange *PostStepDoIt(const G4Track &track,
                                  const G4Step &step) override;

  // Thread-safe counters (accumulated across all worker threads).
  static G4int GetTotalCount()    { return sTotal.load(); }
  static G4int GetDesiredCount()  { return sDesired.load(); }
  static G4int GetRollbackCount() { return sRollback.load(); }
  static void  ResetCounts();

private:
  G4double   fXSScaling;
  ChannelSig fDesiredChannel;                    // sorted (Z,A) pairs

  // Returned for rejected interactions: alpha continues unchanged.
  G4ParticleChange fNullChange;

  static std::atomic<int> sTotal;
  static std::atomic<int> sDesired;
  static std::atomic<int> sRollback;

  // Build sorted (Z,A) nuclear channel signature from a particle change.
  static ChannelSig BuildChannelSig(const G4VParticleChange *pc,
                                    const G4Track *track);

  bool IsDesiredChannel(const ChannelSig &sig) const;
};

// ---------------------------------------------------------------------------
/**
 * GateChannelSelectiveWrapperPhysics
 *
 * G4VPhysicsConstructor that locates the alphaInelastic process on the alpha
 * particle's G4ProcessManager (registered by the base physics list), wraps it
 * with GateChannelSelectiveWrapper, and registers the wrapper in its place.
 *
 * Must be registered via G4VModularPhysicsList::RegisterPhysics() *after* the
 * base physics list is chosen, so that alphaInelastic is already present when
 * ConstructProcess() is called during G4RunManager::Initialize().
 *
 * Usage (Python):
 *   sim.physics_manager.add_channel_xs_scaling(
 *       xs_scaling=10.0, desired_channel=[[2,3],[0,1]])
 */
class GateChannelSelectiveWrapperPhysics : public G4VPhysicsConstructor {
public:
  GateChannelSelectiveWrapperPhysics(G4double xsScaling,
                                      const std::vector<std::vector<int>> &desiredChannel);
  ~GateChannelSelectiveWrapperPhysics() override = default;

  void ConstructParticle() override {}
  void ConstructProcess() override;

  // Forwarded to GateChannelSelectiveWrapper statics for Python access.
  static G4int GetTotalCount()    { return GateChannelSelectiveWrapper::GetTotalCount(); }
  static G4int GetDesiredCount()  { return GateChannelSelectiveWrapper::GetDesiredCount(); }
  static G4int GetRollbackCount() { return GateChannelSelectiveWrapper::GetRollbackCount(); }
  static void  ResetCounts()      { GateChannelSelectiveWrapper::ResetCounts(); }

private:
  G4double fXSScaling;
  std::vector<std::vector<int>> fDesiredChannel;
};

#endif
