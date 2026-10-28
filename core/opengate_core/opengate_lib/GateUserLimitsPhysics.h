/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUserLimitsPhysics_h
#define GateUserLimitsPhysics_h

#include <G4VPhysicsConstructor.hh>

#include <string>
#include <vector>

/*
  Geant4 physics constructor adding the processes which enforce the G4UserLimits
  attached to the regions: G4StepLimiter for the maximum step size and
  G4UserSpecialCuts for the other user limits.

  It reproduces the particle selection of G4StepLimiterPhysics: "all" applies
  both processes to every particle, "all_charged" applies only the step limiter
  to charged particles, and an explicit particle list applies both processes to
  the listed particles.

  Everything is implemented in C++ on purpose. Geant4 calls ConstructProcess on
  every worker thread from G4MTRunManager::Initialize(), while the master thread
  may hold the MT barrier. A Python implementation has to re-enter the
  interpreter on each worker and takes the GIL, which can deadlock the
  initialisation when the main thread holds the GIL while waiting for the
  barrier (see #1163).
*/
class GateUserLimitsPhysics : public G4VPhysicsConstructor {
public:
  GateUserLimitsPhysics(const std::vector<std::string> &particleNames,
                        bool applyToAll, bool applyToAllCharged);

  ~GateUserLimitsPhysics() override = default;

  void ConstructParticle() override;

  void ConstructProcess() override;

private:
  std::vector<G4String> fParticleNames;
  bool fApplyToAll = false;
  bool fApplyToAllCharged = false;
};

#endif // GateUserLimitsPhysics_h
