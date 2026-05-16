/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GEOMETRY_UTILS_HH
#define GEOMETRY_UTILS_HH

#include "G4String.hh"
#include "G4VTouchable.hh"
#include <vector>

/**
 * Finds all unique instances of a Logical Volume and returns their touchable
 * histories.
 *
 * This function traverses the geometry tree, starting from the requested world
 * volume(s), and builds a G4TouchableHistory for every unique path. If the
 * logical volume at the end of a path matches the `targetLVName`, its
 * touchable history is stored.
 *
 * @param targetLVName The name of the logical volume to search for (e.g.,
 * "pet_crystal").
 * @param worldName If non-empty, restrict the search to this world only.
 * If empty, traverse all currently known worlds.
 * @return A vector of pointers to G4VTouchable objects.
 **/
std::vector<std::unique_ptr<G4VTouchable>>
FindAllTouchables(const G4String &targetLVName, const G4String &worldName = "");

void FindAndBuildTouchables(G4VPhysicalVolume *currentVolume,
                            G4NavigationHistory &navHistory,
                            const G4String &targetLVName,
                            std::vector<std::unique_ptr<G4VTouchable>> &results,
                            const G4String &worldName);

#endif // GEOMETRY_UTILS_HH
