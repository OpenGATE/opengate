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
 */
void FindAndBuildTouchables(
    G4VPhysicalVolume *currentVolume, G4NavigationHistory &navHistory,
    const G4String &targetLVName,
    std::vector<std::unique_ptr<G4VTouchable>> &results) {
  // 1. Add the current volume to the navigation history path.
  if (currentVolume->GetName() != "world")
    navHistory.NewLevel(currentVolume, kNormal, currentVolume->GetCopyNo());

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
    FindAndBuildTouchables(daughterVolume, navHistory, targetLVName, results);
  }

  // 4. Backtrack: Remove the current level from the navigation history.
  navHistory.BackLevel();
}

std::vector<std::unique_ptr<G4VTouchable>>
FindAllTouchables(const G4String &targetLVName) {
  std::vector<std::unique_ptr<G4VTouchable>> touchableResults;

  // Get the world volume directly from the RunManager and DetectorConstruction.
  const auto pvs = G4PhysicalVolumeStore::GetInstance();
  const auto worldVolume = pvs->GetVolume("world");

  if (!worldVolume) {
    Fatal("FindAllTouchables, cannot find the World Volume. The geometry is "
          "not initialized.");
  }

  // Create the G4NavigationHistory object that will be built up during
  // recursion.
  G4NavigationHistory navHistory;

  // Start the recursive search from the world volume.
  navHistory.SetFirstEntry(worldVolume);
  FindAndBuildTouchables(worldVolume, navHistory, targetLVName,
                         touchableResults);

  return touchableResults;
}
