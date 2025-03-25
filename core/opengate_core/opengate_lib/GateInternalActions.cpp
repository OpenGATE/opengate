#include <G4DNAChemistryManager.hh>
#include <G4EventManager.hh>

#include "GateInternalActions.h"

void GateInternalActions::NewStage() {
  if (fChemistryEnabled) {
    auto *stackManager = G4EventManager::GetEventManager()->GetStackManager();
    if (stackManager != nullptr && stackManager->GetNTotalTrack() == 0) {
      G4DNAChemistryManager::Instance()->Run();
    }
  }
}
