/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUserLimitsPhysics.h"

#include <G4ParticleDefinition.hh>
#include <G4ProcessManager.hh>
#include <G4StepLimiter.hh>
#include <G4UserSpecialCuts.hh>

#include <algorithm>

GateUserLimitsPhysics::GateUserLimitsPhysics(
    const std::vector<std::string> &particleNames, bool applyToAll,
    bool applyToAllCharged)
    : G4VPhysicsConstructor("UserLimitsPhysics"),
      fParticleNames(particleNames.begin(), particleNames.end()),
      fApplyToAll(applyToAll), fApplyToAllCharged(applyToAllCharged) {}

void GateUserLimitsPhysics::ConstructParticle() {}

void GateUserLimitsPhysics::ConstructProcess() {
  // This method is called by Geant4 on each worker thread during
  // G4MTRunManager::Initialize(), while the master thread may hold the MT
  // barrier. It must therefore not acquire the GIL: everything below is pure
  // C++, and the processes are created in the calling thread's process table.
  auto *stepLimiter = new G4StepLimiter("StepLimiter");
  auto *userSpecialCuts = new G4UserSpecialCuts("UserSpecialCut");

  auto *particleIterator = GetParticleIterator();
  particleIterator->reset();
  while ((*particleIterator)()) {
    G4ParticleDefinition *particle = particleIterator->value();
    G4ProcessManager *processManager = particle->GetProcessManager();
    const G4String particleName = particle->GetParticleName();

    bool addStepLimiter = false;
    bool addUserSpecialCuts = false;
    if (fApplyToAll || std::find(fParticleNames.begin(), fParticleNames.end(),
                                 particleName) != fParticleNames.end()) {
      addStepLimiter = true;
      addUserSpecialCuts = true;
    } else if (fApplyToAllCharged && particle->GetPDGCharge() != 0) {
      // reproduces the logic of Geant4's G4StepLimiterPhysics: only the step
      // limiter is added to charged particles
      addStepLimiter = true;
    }

    if (addStepLimiter) {
      processManager->AddDiscreteProcess(stepLimiter);
    }
    if (addUserSpecialCuts) {
      processManager->AddDiscreteProcess(userSpecialCuts);
    }
  }
}
