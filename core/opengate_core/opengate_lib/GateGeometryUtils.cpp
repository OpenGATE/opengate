/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4LogicalVolume.hh"
#include "G4Navigator.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4RunManager.hh"
#include "G4TouchableHistory.hh"
#include "G4TransportationManager.hh"
#include "G4VPhysicalVolume.hh"

#include "GateGeometryUtils.h"
#include "GateHelpers.h"
#include "GateUniqueVolumeIDManager.h"

/**
 * @brief Recursively builds the path to each volume using a
 * G4NavigationHistory. When a target is found, it constructs a
 * G4TouchableHistory from the completed navigation history and saves it.
 *
 * @param currentVolume The volume to process in this call.
 * @param navHistory The navigation history being built during the traversal.
 * @param targetLVName The name of the logical volume we are searching for.
 * @param results The final vector where valid touchables are stored.
 * @param worldName The name of the world being traversed (for debugging).
 */
void FindAndBuildTouchables(G4VPhysicalVolume *currentVolume,
                            G4NavigationHistory &navHistory,
                            const G4String &targetLVName,
                            std::vector<std::unique_ptr<G4VTouchable>> &results,
                            const G4String &worldName) {

  // 1. Add the current volume to the navigation history path.
  // Skip the world volume itself (it's already set as the first entry)
  if (currentVolume->GetName() != worldName) {
    navHistory.NewLevel(currentVolume, kNormal, currentVolume->GetCopyNo());
  }

  // 2. Check if the current volume's LV is the one we are looking for.
  const G4LogicalVolume *currentLV = currentVolume->GetLogicalVolume();

  if (currentLV->GetName() == targetLVName) {
    // We found a match, construct a new G4TouchableHistory
    // by copying the G4NavigationHistory.
    // WARNING: we create a G4TouchableHistory from the G4NavigationHistory
    // the volumes are stored in reverse order:
    // G4NavigationHistory->GetVolume(0) is the world
    // G4TouchableHistory->GetVolume(0) is the last volume
    results.emplace_back(std::make_unique<G4TouchableHistory>(navHistory));
  }

  // 3. Recurse into all daughter volumes.
  for (size_t i = 0; i < currentLV->GetNoDaughters(); ++i) {
    G4VPhysicalVolume *daughterVolume = currentLV->GetDaughter(i);
    FindAndBuildTouchables(daughterVolume, navHistory, targetLVName, results,
                           worldName);
  }

  // 4. Backtrack: Remove the current level from the navigation history.
  if (currentVolume->GetName() != worldName) {
    navHistory.BackLevel();
  }
}

std::vector<std::unique_ptr<G4VTouchable>>
FindAllTouchables(const G4String &targetLVName) {
  std::vector<std::unique_ptr<G4VTouchable>> touchableResults;

  // Get the transportation manager to access all worlds
  G4TransportationManager *transportMgr =
      G4TransportationManager::GetTransportationManager();

  if (!transportMgr) {
    Fatal("FindAllTouchables: Cannot get G4TransportationManager. "
          "The geometry is not initialized.");
  }

  // Get the iterator to all navigators (one per world: mass world + parallel
  // worlds)
  const auto navigatorsBegin = transportMgr->GetActiveNavigatorsIterator();

  // Get the number of worlds to know how many navigators to iterate through
  const size_t numWorlds = transportMgr->GetNoWorlds();

  if (numWorlds == 0) {
    Fatal("FindAllTouchables: No worlds found. "
          "The geometry is not initialized.");
  }

  // Iterate through all navigators
  for (size_t i = 0; i < numWorlds; ++i) {
    const G4Navigator *navigator = *(navigatorsBegin + i);

    if (!navigator) {
      DDD("Warning: Navigator " + std::to_string(i) + " is null");
      continue;
    }

    G4VPhysicalVolume *worldVolume = navigator->GetWorldVolume();
    if (!worldVolume) {
      DDD("Warning: World volume for navigator " + std::to_string(i) +
          " is null");
      continue;
    }

    const G4String worldName = worldVolume->GetName();

    // Create a navigation history for this world
    G4NavigationHistory navHistory;
    navHistory.SetFirstEntry(worldVolume);

    // Start the recursive search from this world volume
    FindAndBuildTouchables(worldVolume, navHistory, targetLVName,
                           touchableResults, worldName);
  }

  return touchableResults;
}
